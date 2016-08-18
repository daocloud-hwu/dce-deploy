#!/bin/bash

set -e

[ "xxx$1" != "xxx" ] && version=":$1"

bash -c "$(docker run --rm -i daocloud.io/daocloud/dce${version} install -q | sed "s/-it/-i/g")"
