#Pull
docker pull algosecure/pollenisator-worker

# Build docker
## Generic command
docker build -t algosecure/pollenisator-worker .
## Rebuild all tools (updated them)
docker build -t algosecure/pollenisator-worker . --no-cache
# Run worker
check and edit config/client.cfg and set host and port to match the IP that is running pollenisator

docker run -v `pwd`:/home/Pollenisator/ -d algosecure/pollenisator-worker

docker run -v `pwd`:/home/Pollenisator/ -ti algosecure/pollenisator-worker /bin/bash

# Stop docker

docker container ls
docker stop Xxxxxxx
