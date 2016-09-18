#!/bin/bash

set -e

if [ "xxx$1" != "xxx" ]; then
  version=":$1"
else
  echo "Usage: $0 <version>"
  exit 1
fi

if [ ! -f /etc/docker/daemon.json.bak ]; then
  cp /etc/docker/daemon.json /etc/docker/daemon.json.bak
fi

service docker restart
bash -c "$(docker run --rm -i daocloud.io/daocloud/dce${version} install -q | sed "s/-it/-i/g")"
service docker restart
