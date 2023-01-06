"""worker module. Execute code and store results in database, files in the SFTP server.
"""

import errno
import os
import ssl
import sys
import uuid
import time
import threading
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from multiprocessing import Process, Queue
from core.Components.apiclient import APIClient
import core.Components.Utils as Utils
from core.Models.Interval import Interval
from core.Models.Tool import Tool
import socketio
import socket

sio = socketio.Client()
running_tasks = {}
myname = ""

def beacon():
    global sio
    global running_tasks
    global myname
    pentest = ""
    if running_tasks:
        pentest = running_tasks[0][0] # pentest
    sio.emit("keepalive", {"name":myname, "running_tasks":[str(x) for x in running_tasks]})
    timer = threading.Timer(5.0, beacon)
    timer.start()

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
    global myname
    myname = os.getenv('POLLENISATOR_WORKER_NAME', str(uuid.uuid4())+"@"+socket.gethostname())
    toolsCfg = Utils.loadToolsConfig()
    sio.emit("register", {"name":myname, "binaries":list(toolsCfg.keys())})
    timer = threading.Timer(5.0, beacon)
    timer.start()
    sio.wait()
    apiclient.unregisterWorker(myname)
  

@sio.event
def executeCommand(data):
    workerToken = data.get("workerToken")
    pentest = data.get("pentest")
    toolId = data.get("toolId")
    infos = data.get("infos")
    q = Queue()
    q_resp = Queue()
    task = Process(target=doExecuteCommand, args=[workerToken, pentest, toolId, q, q_resp, infos]) 
    global running_tasks
    
    running_tasks[toolId] = [pentest, toolId, task, q, q_resp]
    task.start()

@sio.event
def deleteWorker(data):
    global running_tasks
    i = 0
    for running in running_tasks.values():
        running[2].terminate()
        running[2].join()
        break
    sio.disconnect()

@sio.event
def getProgress(data): 
    toolId = data.get("tool_iid")
    msg = getToolProgress(toolId)
    print(msg)
    sio.emit("getProgressResult", {"result":msg})

def getToolProgress(toolId):
    global running_tasks
    pentest, toolId, task, q, q_resp= running_tasks.get(str(toolId), (None, None,None, None, None))
    if task is None or q is None:
        return ""
    progress = ""
    if task.is_alive():
        q.put("\n")
        progress = q_resp.get()
        return progress
    return ""

def doExecuteCommand(workerToken, calendarName, toolId, queue, queueResponse, infos):
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
    if command_dict is None and toolModel.text != "":
        command_dict = {"plugin":toolModel.plugin_used, "timeout":0}
    msg = ""
    success, comm, fileext = apiclient.getCommandline(toolId)
    if not success:
        print(str(comm))
        toolModel.setStatus(["error"])
        return False, str(comm)
    
    outputRelDir = toolModel.getOutputDir(apiclient.currentPentest)
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
    toolsCfg = Utils.loadToolsConfig()
    bin_path = toolsCfg.get(command_dict.get("bin_path"))
    if bin_path is None:
        toolModel.setStatus(["error"])
        toolModel.notes = str(toolModel.name)+" : no binary path setted"
        return False, str(toolModel.name)+" : no binary path setted"
    comm = bin_path + " " + comm
    toolModel.updateInfos({"cmdline":comm})
    ##
    if "timedout" in toolModel.status:
        timeLimit = None
    # Get tool's wave time limit searching the wave intervals
    if toolModel.wave == "Custom commands":
        timeLimit = None
    else:
        timeLimit = getWaveTimeLimit(toolModel.wave)
    # adjust timeLimit if the command has a lower timeout
    if command_dict is not None and timeLimit is not None: 
        timeLimit = min(datetime.now()+timedelta(0, int(command_dict.get("timeout", 0))), timeLimit)
    
    try:
        global myname
        
        toolModel.markAsRunning(myname, infos)
        print(('TASK STARTED:'+toolModel.name))
        print("Will timeout at "+str(timeLimit))
        # Execute the command with a timeout
        returncode, stdout = Utils.execute(comm, timeLimit, True, queue, queueResponse)
        if returncode == -1:
            toolModel.setStatus(["timedout"])
            return False, str("timedout")
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
    return True, outputfile

@sio.event
def stopCommand(data):
    pentest = data.get("pentest")
    tool_iid = data.get("tool_iid")
    global running_tasks
    i = 0
    deleted = None
    for key, running in running_tasks.items():
        if running[0] == pentest and running[1] == tool_iid:
            print("STOPPING command "+str(tool_iid)+" ...")
            running[2].terminate()
            running[2].join()
            deleted = key
            print("STOPPING command "+str(tool_iid)+" ... Done")
            break
        i += 1
    if i < len(running_tasks):
        del running_tasks[deleted]


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