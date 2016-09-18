#!/bin/bash

docker swarm leave --force > /dev/null 2>&1
docker ps -a | awk '{print $1}' | grep -v "CONTAINER" | xargs docker rm -vf > /dev/null 2>&1

rm -rf /var/local/dce
rm -rf /etc/daocloud/dce

if [ -f /etc/docker/daemon.json.bak ]; then
  cat /etc/docker/daemon.json.bak > /etc/docker/daemon.json
fi
