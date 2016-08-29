#!/bin/bash

docker swarm leave --force > /dev/null 2>&1
docker ps -a | awk '{print $1}' | grep -v "CONTAINER" | xargs docker rm -vf > /dev/null 2>&1

rm -rf /var/local/dce
rm -rf /etc/daocloud/dce
rm -rf /etc/docker/daemon.json
