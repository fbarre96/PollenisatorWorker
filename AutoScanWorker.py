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
from core.Models.Command import Command
import socket



def main():
    """Main function. Start a worker instance
    """
    apiclient = APIClient.getInstance()
    tools_to_register = Utils.loadToolsConfig()
    print("Registering commands : "+str(list(tools_to_register.keys())))
    myname = str(uuid.uuid4())+"@"+socket.gethostname()
    apiclient.registeredCommands(myname, list(tools_to_register.keys()))
    p = Process(target=workerLoop, args=(myname,))
    try:
        p.start()
        p.join()
    except(KeyboardInterrupt, SystemExit):
        pass

def workerLoop(workerName):
    """
    Start monitoring events
    Will stop when receiving a KeyboardInterrupt
    Args:
        calendar: the pentest database name to monitor
    """
    print("Starting worker thread")
    functions = {
        "executeCommand": executeCommand,
        "editToolConfig": editToolConfig,
    }
    running_tasks = []
    apiclient = APIClient.getInstance()
    try:
        while(True):
            time.sleep(3)
            instructions = apiclient.fetchWorkerInstruction(workerName)
            if instructions is None:
                continue
            for instruction in instructions:
                if instruction["function"] in functions:
                    task = Process(target = functions[instruction["function"]], args=instruction["args"])
                    task.start()
                if instruction["function"] == "executeCommand":
                    running_tasks.append(instruction["args"]+[task])
                elif instruction["function"] == "stopCommand":
                    stopCommand(*instruction["args"], running_tasks)

    except(KeyboardInterrupt, SystemExit):
        print("stop received...")
        apiclient.unregisterWorker(workerName)

def launchTask(workerToken, calendarName, worker, launchableTool):
    launchableToolId = launchableTool.getId()
    launchableTool.markAsRunning(worker)
    # Mark the tool as running (scanner_ip is set and dated is set, datef is "None")
    from AutoScanWorker import executeCommand
    print("Launching command "+str(launchableTool))
    p = Process(target=executeCommand, args=(workerToken, calendarName, launchableToolId))
    p.start()
    # Append to running tasks this  result and the corresponding tool id
    return True

def editToolConfig(command_name, remote_bin, plugin):
    tools_to_register = Utils.loadToolsConfig()
    tools_to_register[command_name] = {"bin":remote_bin, "plugin":plugin}
    Utils.saveToolsConfig(tools_to_register)

def executeCommand(workerToken, calendarName, toolId, parser=""):
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
    # Connect to given calendar
    apiclient = APIClient.getInstance()
    apiclient.setToken(workerToken)
    apiclient.currentPentest = calendarName # by pass login
    toolModel = Tool.fetchObject({"_id":ObjectId(toolId)})
    command_o = toolModel.getCommand()
    msg = ""
    ##
    success, comm, fileext = apiclient.getCommandline(toolId, parser)
    if not success:
        print(str(comm))
        toolModel.setStatus(["error"])
        return False, str(comm)
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
    if command_o is not None:
        timeLimit = min(datetime.now()+timedelta(0, int(command_o.get("timeout", 0))), timeLimit)
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
    msg = apiclient.importToolResult(toolId, parser, outputfile)
    if msg != "Success":
        #toolModel.markAsNotDone()
        print(str(msg))
        toolModel.setStatus(["error"])
        return False, str(msg)
          
    # Delay
    if command_o is not None:
        if float(command_o.get("sleep_between", 0)) > 0.0:
            msg += " (will sleep for " + \
                str(float(command_o.get("sleep_between", 0)))+")"
        print(msg)
        time.sleep(float(command_o.get("sleep_between", 0)))
    return True, ""
    
def stopCommand(pentest, tool_iid, running_tasks):
    i = 0
    for running in running_tasks:
        if running[0] == pentest and running[1] == tool_iid:
            print("STOPPING command "+str(tool_iid)+" ...")
            running[3].terminate()
            running[3].join()
            print("STOPPING command "+str(tool_iid)+" ... Done")
            break
        i += 1
    del running_tasks[i]

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
