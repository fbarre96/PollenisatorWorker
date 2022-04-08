"""Tool Model. A tool is an instanciation of a command against a target"""

from core.Models.Element import Element
from core.Components.apiclient import APIClient
from bson.objectid import ObjectId
from datetime import datetime

class Tool(Element):
    """
    Represents a Tool object that defines a tool. A tool is a command run materialized on a runnable object (wave, scope, ip, or port)

    Attributes:
        coll_name: collection name in pollenisator database
    """
    coll_name = "tools"

    def __init__(self, valuesFromDb=None):
        """Constructor
        Args:
            valueFromDb: a dict holding values to load into the object. A mongo fetched interval is optimal.
                        possible keys with default values are : _id(None), parent(None), tags([]), infos({}),
                        command_iid(""), wave(""),  name(""), scope(""), ip(""), port(""), proto("tcp"), lvl(""), text(""), dated("None"),
                        datef("None"), scanner_ip("None"), status([]), notes(""), resultfile("")
        """
        if valuesFromDb is None:
            valuesFromDb = {}
        super().__init__(valuesFromDb.get("_id", None), valuesFromDb.get("parent", None), valuesFromDb.get(
            "tags", []), valuesFromDb.get("infos", {}))
        self.datef = "None"
        self.dated = "None"
        self.scanner_ip = "None"
        self.resultfile = ""
        self.status = []
        self.initialize(valuesFromDb.get("command_iid", ""), valuesFromDb.get("wave", ""),
                        valuesFromDb.get("name", ""),
                        valuesFromDb.get(
                            "scope", ""), valuesFromDb.get("ip", ""),
                        str(valuesFromDb.get("port", "")), valuesFromDb.get(
                            "proto", "tcp"),
                        valuesFromDb.get(
                            "lvl", ""), valuesFromDb.get("text", ""),
                        valuesFromDb.get("dated", "None"), valuesFromDb.get(
                            "datef", "None"),
                        valuesFromDb.get(
                            "scanner_ip", "None"), valuesFromDb.get("status", []), valuesFromDb.get("notes", ""), valuesFromDb.get("resultfile", ""), valuesFromDb.get("tags", []), valuesFromDb.get("infos", {}))

    def initialize(self, command_iid, wave="", name="", scope="", ip="", port="", proto="tcp", lvl="", text="",
                   dated="None", datef="None", scanner_ip="None", status=None, notes="", resultfile="", tags=None, infos=None):
        
        """Set values of tool
        Args:
            command_iid: command associated for the tool 
            name: name of the tool (should match a command name)
            wave: the target wave name of this tool (only if lvl is "wave"). Default  ""
            scope: the scope string of the target scope of this tool (only if lvl is "network"). Default  ""
            ip: the target ip "ip" of this tool (only if lvl is "ip" or "port"). Default  ""
            port: the target port "port number" of this tool (only if lvl is "port"). Default  ""
            proto: the target port "proto" of this tool (only if lvl is "port"). Default  "tcp"
            lvl: the tool level of exploitation (wave, network, ip ort port/). Default ""
            text: the command to be launched. Can be empty if name is matching  a command. Default ""
            dated: a starting date and tiem for this interval in format : '%d/%m/%Y %H:%M:%S'. or the string "None"
            datef: an ending date and tiem for this interval in format : '%d/%m/%Y %H:%M:%S'. or the string "None"
            scanner_ip: the worker name that performed this tool. "None" if not performed yet. Default is "None"
            status: a list of status string describing this tool state. Default is None. (Accepted values for string in list are done, running, OOT, OOS)
            notes: notes concerning this tool (opt). Default to ""
            resultfile: an output file generated by the tool. Default is ""
            tags: a list of tags
            infos: a dictionnary of additional info
        Returns:
            this object
        """
        self.command_iid = command_iid
        self.name = name
        self.wave = wave
        self.scope = scope
        self.ip = ip
        self.port = str(port)
        self.proto = proto
        self.lvl = lvl
        self.text = text
        self.dated = dated
        self.datef = datef
        self.scanner_ip = scanner_ip
        self.notes = notes
        self.resultfile = resultfile
        self.tags = tags if tags is not None else []
        self.infos = infos if infos is not None else {}
        if status is None:
            status = []
        elif isinstance(status, str):
            status = [status]
        self.status = status
        return self

    def delete(self):
        """
        Delete the tool represented by this model in database.
        """
        apiclient = APIClient.getInstance()
        apiclient.delete("tools", ObjectId(self._id))

    def addInDb(self):
        """
        Add this tool in database.

        Returns: a tuple with :
                * bool for success
                * mongo ObjectId : already existing object if duplicate, create object id otherwise 
        """
        base = self.getDbKey()
        apiclient = APIClient.getInstance()
        # Checking unicity
        existing = apiclient.find("tools", base, False)
        if existing is not None:
            return False, existing["_id"]
        # Those are added to base after tool's unicity verification
        base["command_iid"] = self.command_iid
        base["scanner_ip"] = self.scanner_ip
        base["dated"] = self.dated
        base["datef"] = self.datef
        if isinstance(self.status, str):
            self.status = [self.status]
        base["status"] = self.status
        base["tags"] = self.tags
        base["text"] = self.text
        base["resultfile"] = self.resultfile
        base["notes"] = self.notes
        res, iid = apiclient.insert("tools", base)
        self._id = iid
        return True, iid
      

    def setStatus(self,status):
        """Set this tool status with given list of status
        Args:
            list of string with status inside (accepted values are OOS, OOT, running, done)
        """
        self.status = status
        apiclient = APIClient.getInstance()
        apiclient.setToolStatus(self, self.status)

    def getStatus(self):
        """
        Get the tool executing status.

        Return:
            Returns a list of status status are :
                OOT : Out of time = This tool is in a wave which does not have any interval for now.
                OOS : Out os scope = This tool is in an IP OOS
                done : This tool is completed
                running : This tool is being run."""
        return self.status

    def getCommand(self):
        """
        Get the tool associated command.

        Return:
            Returns the Mongo dict command fetched instance associated with this tool's name.
        """
        apiclient = APIClient.getInstance()
        commandTemplate = apiclient.findInDb(apiclient.getCurrentPentest(),
                                                 "commands", {"_id": ObjectId(self.command_iid)}, False)
        return commandTemplate

    @classmethod
    def __sanitize(cls, var_to_path):
        """Replace unwanted chars in variable given: '/', ' ' and ':' are changed to '_'
        Args:
            var_to_path: a string to sanitize to use a path folder
        Returns:
            modified arg as string
        """
        var_to_path = var_to_path.replace("/", "_")
        var_to_path = var_to_path.replace(" ", "_")
        var_to_path = var_to_path.replace(":", "_")
        return var_to_path

    def getOutputDir(self, calendarName):
        """
        Get the tool required output directory path.
        Args:
            calendarName: the pentest database name
        Return:
            Returns the output directory of this tool instance.
        """
        # get command needed directory
        output_dir = Tool.__sanitize(
            calendarName)+"/"+Tool.__sanitize(self.name)+"/"
        if self.wave != "" and self.wave is not None:
            output_dir += Tool.__sanitize(self.wave)+"/"
        if self.scope != "" and self.scope is not None:
            output_dir += Tool.__sanitize(self.scope)+"/"
        if self.ip != "" and self.ip is not None:
            output_dir += Tool.__sanitize(self.ip)+"/"
        if self.port != "" and self.port is not None:
            port_dir = str(self.port) if str(self.proto) == "tcp" else str(
                self.proto)+"/"+str(self.port)
            output_dir += Tool.__sanitize(port_dir)+"/"
        return output_dir

    

    def update(self, pipeline_set=None):
        """Update this object in database.
        Args:
            pipeline_set: (Opt.) A dictionnary with custom values. If None (default) use model attributes.
        """
        apiclient = APIClient.getInstance()
        if pipeline_set is None:
            apiclient.update("tools", ObjectId(self._id), {"scanner_ip": str(self.scanner_ip), "dated": str(self.dated), "status": self.status,
                         "datef":  str(self.datef), "notes":  self.notes, "resultfile": self.resultfile, "tags": self.tags})
        else:
            apiclient.update(
                "tools", ObjectId(self._id), pipeline_set)

    def _getParentId(self):
        """
        Return the mongo ObjectId _id of the first parent of this object. For a Tool it is either a scope, an ip or a port depending on the tool's level.

        Returns:
            Returns the parent's ObjectId _id". or None if a type error occurs
        """
        apiclient = APIClient.getInstance()
        try:
            if self.lvl == "wave":
                wave = apiclient.find("waves", {"wave": self.wave}, False)
                return wave["_id"]
            elif self.lvl == "network" or self.lvl == "domain":
                return apiclient.find("scopes", {"wave": self.wave, "scope": self.scope}, False)["_id"]
            elif self.lvl == "ip":
                return apiclient.find("ips", {"ip": self.ip}, False)["_id"]
            else:
                return apiclient.find("ports", {"ip": self.ip, "port": self.port, "proto": self.proto}, False)["_id"]
        except TypeError:
            # None type returned:
            return None

    def __str__(self):
        """
        Get a string representation of a tool.

        Returns:
            Returns the tool name. The wave name is prepended if tool lvl is "port" or "ip"
        """
        ret = self.name
        if self.lvl == "ip" or self.lvl == "port":
            ret = self.wave+"-"+ret
        return ret

    def getDetailedString(self):
        """
        Get a more detailed string representation of a tool.

        Returns:
            string
        """
        if self.lvl == "network" or self.lvl == "domain":
            return str(self.scope)+" "+str(self)
        elif self.lvl == "ip":
            return str(self.ip)+" "+str(self)
        else:
            return str(self.ip)+":"+str(self.proto+"/"+self.port)+" "+str(self)

    def getResultFile(self):
        """Returns the result file of this tool
        Returns:
            strings
        """
        return self.resultfile

    

    def markAsRunning(self, workerName):
        """Set this tool status as running but keeps OOT or OOS.
        Sets the starting date to current time and ending date to "None"
        Args:
            workerName: the worker name that is running this tool
        """
        self.dated = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        self.datef = "None"
        newStatus = ["running"]
        if "OOS" in self.status:
            newStatus.append("OOS")
        if "OOT" in self.status:
            newStatus.append("OOT")
        self.status = newStatus
        self.scanner_ip = workerName
        self.update()

    def markAsNotDone(self):
        """Set this tool status as not done by removing "done" or "running" status.
        Also resets starting and ending date as well as worker name
        """
        self.dated = "None"
        self.datef = "None"
        self.scanner_ip = "None"
        if "done" in self.status:
            self.status.remove("done")
        if "running" in self.status:
            self.status.remove("running")
        if not self.status:
            self.status = ["ready"]
        self.update()

    

    def getDbKey(self):
        """Return a dict from model to use as unique composed key.
        Returns:
            A dict (7 keys :"wave", "scope", "ip", "port", "proto", "name", "lvl")
        """
        base = {"wave": self.wave, "scope": "", "ip": "", "port": "",
                "proto": "", "name": self.name, "lvl": self.lvl}
        if self.lvl == "wave":
            return base
        if self.lvl in ("domain", "network"):
            base["scope"] = self.scope
            return base
        base["ip"] = self.ip
        if self.lvl == "ip":
            return base
        base["port"] = self.port
        base["proto"] = self.proto
        return base
