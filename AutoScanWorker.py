"""worker module. Execute code and store results in database, files in the SFTP server.
"""

import errno
import os
import ssl
import sys
import uuid
import time
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from multiprocessing import Process
from core.Components.apiclient import APIClient
import core.Components.Utils as Utils
from core.Models.Interval import Interval
from core.Models.Tool import Tool
import socketio
import socket

sio = socketio.Client()
running_tasks = []

def main():
    """Main function. Start a worker instance
    """
    global sio
    apiclient = APIClient.getInstance()
    if apiclient.tryConnection():
        sio.connect(apiclient.api_url)
    else:
        print("Unable to reach the API "+str(apiclient.api_url))
        sys.exit(0)
    myname = os.getenv('POLLENISATOR_WORKER_NAME', str(uuid.uuid4())+"@"+socket.gethostname())
    sio.emit("register", {"name":myname})
    sio.wait()
    apiclient.unregisterWorker(myname)
  

@sio.event
def executeCommand(data):
    workerToken = data.get("workerToken")
    pentest = data.get("pentest")
    toolId = data.get("toolId")
    task = Process(target=doExecuteCommand, args=[workerToken, pentest, toolId]) 
    global running_tasks
    running_tasks.append([pentest, toolId, task])
    task.start()

def doExecuteCommand(workerToken, calendarName, toolId):
    """
    remote task
    Execute the tool with the given toolId on the given calendar name.
    Then execute the plugin corresponding.
    Any unhandled exception will result in a task-failed event in the class.

    Args:
        calendarName: The calendar to search the given tool id for.
        toolId: the mongo Object id corresponding to the tool to execute.
        parser: plugin name to execute. If empty, the plugin specified in tools.d will be feteched.
    Raises:
        Terminated: if the task gets terminated
        OSError: if the output directory cannot be created (not if it already exists)
        Exception: if an exception unhandled occurs during the bash command execution.
        Exception: if a plugin considered a failure.
    """
    apiclient = APIClient.getInstance()
    apiclient.setToken(workerToken) 
    apiclient.currentPentest = calendarName # bypass login by not using connectToDb
    toolModel = Tool.fetchObject({"_id":ObjectId(toolId)})
    command_dict = toolModel.getCommand()
    msg = ""
    success, comm, fileext = apiclient.getCommandline(toolId)
    if not success:
        print(str(comm))
        toolModel.setStatus(["error"])
        return False, str(comm)
    bin_path = command_dict["bin_path"]
    if bin_path is not None:
        if not bin_path.endswith(" "):
            bin_path = bin_path+" "
    comm = bin_path+comm
    outputRelDir = toolModel.getOutputDir(calendarName)
    abs_path = os.path.dirname(os.path.abspath(__file__))
    toolFileName = toolModel.name+"_" + \
            str(time.time()) # ext already added in command
    outputDir = os.path.join(abs_path, "./results", outputRelDir)
    
    # Create the output directory
    try:
        os.makedirs(outputDir)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(outputDir):
            pass
        else:
            print(str(exc))
            toolModel.setStatus(["error"])
            return False, str(exc)
    outputDir = os.path.join(outputDir, toolFileName)
    comm = comm.replace("|outputDir|", outputDir)
    # Get tool's wave time limit searching the wave intervals
    if toolModel.wave == "Custom commands":
        timeLimit = None
    else:
        timeLimit = getWaveTimeLimit(toolModel.wave)
    # adjust timeLimit if the command has a lower timeout
    if command_dict is not None:
        timeLimit = min(datetime.now()+timedelta(0, int(command_dict.get("timeout", 0))), timeLimit)
    ##
    if "timedout" in toolModel.status:
        timeLimit = None
    try:
        print(('TASK STARTED:'+toolModel.name))
        print("Will timeout at "+str(timeLimit))
        # Execute the command with a timeout
        returncode = Utils.execute(comm, timeLimit, True)
        if returncode == -1:
            toolModel.setStatus(["timedout"])
            return False, str("Command timedout")
    except Exception as e:
        print(str(e))
        toolModel.setStatus(["error"])
        return False, str(e)
    # Execute found plugin if there is one
    outputfile = outputDir+fileext
    plugin = "auto-detect" if command_dict["plugin"] == "" else command_dict["plugin"]
    msg = apiclient.importToolResult(toolId, plugin, outputfile)
    if msg != "Success":
        #toolModel.markAsNotDone()
        print(str(msg))
        toolModel.setStatus(["error"])
        return False, str(msg)
          
    # Delay
    if command_dict is not None:
        if float(command_dict.get("sleep_between", 0)) > 0.0:
            msg += " (will sleep for " + \
                str(float(command_dict.get("sleep_between", 0)))+")"
        print(msg)
        time.sleep(float(command_dict.get("sleep_between", 0)))
    return True, ""

@sio.event
def stopCommand(data):
    pentest = data.get("pentest")
    tool_iid = data.get("tool_iid")
    global running_tasks
    i = 0
    for running in running_tasks:
        if running[0] == pentest and running[1] == tool_iid:
            print("STOPPING command "+str(tool_iid)+" ...")
            running[2].terminate()
            running[2].join()
            print("STOPPING command "+str(tool_iid)+" ... Done")
            break
        i += 1
    if i < len(running_tasks):
        del running_tasks[i]


# @sio.event
# def editToolConfig(data):
#     command_name = data["command_name"]
#     tools_to_register = Utils.loadToolsConfig()
#     tools_to_register[command_name] = {"bin":data.get("remote_bin"), "plugin":data.get("plugin")}
#     Utils.saveToolsConfig(tools_to_register)


def getWaveTimeLimit(waveName):
    """
    Return the latest time limit in which this tool fits. The tool should timeout after that limit

    Returns:
        Return the latest time limit in which this tool fits.
    """
    intervals = Interval.fetchObjects({"wave": waveName})
    furthestTimeLimit = datetime.now()
    for intervalModel in intervals:
        if Utils.fitNowTime(intervalModel.dated, intervalModel.datef):
            endingDate = intervalModel.getEndingDate()
            if endingDate is not None:
                if endingDate > furthestTimeLimit:
                    furthestTimeLimit = endingDate
    return furthestTimeLimit

if __name__ == '__main__':
    main()