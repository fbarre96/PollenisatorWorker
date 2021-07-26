![pollenisator_flat](https://github.com/AlgoSecure/Pollenisator/wiki/uploads/1e17b6e558bec07767eb12506ed6b2bf/pollenisator_flat.png)

**Pollenisator** is a tool aiming to assist pentesters and auditor automating the use of some tools/scripts and keep track of them.
  * Written in python 3
  * Provides a modelisation of "pentest objects" : Scope, Hosts, Ports, Commands, Tools etc.
  * Tools/scripts are separated into 4 categories : wave, Network/domain, IP, Port
  * Objects are stored in a NoSQL DB (Mongo)
  * Keep links between them to allow queries
  * Objects can be created through parsers / manual input
  * Business logic can be implemented (auto vuln referencing, item triggers, etc.)
  * Many tools/scripts launch conditions are availiable to avoid overloading the target or the scanner.
  * A GUI based on tcl/tk
  
## Documentation ##

Everything is the [wiki](https://github.com/AlgoSecure/Pollenisator/wiki/_Sidebar), including [installation](https://github.com/Algosecure/Pollenisator/wiki/Overview)

## Install Docker (default tools) ##
If not cloned yet , clone it:

`$ git clone https://github.com/Algosecure/PollenisatorWorker.git`

`$ cd PollenisatorWorker`

This docker takes me ~9 minutes to install on a 10 Mbps connection and 5 minutes to install on high speed connection (255 Mbps).

It comes with all the tools described in [this page](https://github.com/Algosecure/Pollenisator/wiki/Default-tools)

Build the docker using this command:

`$ docker build -t pollenisatorworker .`

## Manual Install ##

**WARNING** : Any user of pollenisator can claim your worker and launch commands on it, which means any user can take control of your worker server.
This why the docker is recommended as it limits what is visible (LAN, home folder...)


A worker is supposed to have a set of tools ready to use. Each of this tool may be installed as you want but then you have to complete the tool configuration file located in the *config/tools.d/* directory

First, clone the PollenisatorWorker repo if not done already

`$ git clone https://github.com/Algosecure/PollenisatorWorker
`$ cd PollenisatorWorker`

Then install requirements :

`$ sudo python3 -m pip install -r requirements.txt`

`$ ./startWorker.sh`

### Install tools

Pollenisator come with plugins and commands. If you want to use them, you have to install [those tools](https://github.com/Algosecure/Pollenisator/wiki/Default-tools)

### Configure tools

To register tools you  have to edit the config/tools.d/tools.json file.
You can do it from the PollenisatorGUI client or from your text editor by adding an item inside the list which looks like [{"<pollenisator_command_name>":{"bin":"<The command line to summon the wanted tool binary/script>", "plugin":"<Pollenisator_plugin.py>"}}]


