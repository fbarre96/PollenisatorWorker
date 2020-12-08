# Build docker
## Generic command
docker build -t pollenisator .

## Rebuild all tools (updated them)
docker build --no-cache -t pollenisator .

# Run worker
check and edit config/client.cfg and set host and port to match the IP that is running pollenisator

docker run -v `pwd`:/home/Pollenisator/ -d pollenisator

docker run -v `pwd`:/home/Pollenisator/ -ti pollenisator /bin/bash

# Stop docker

docker container ls
docker stop Xxxxxxx
