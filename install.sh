#!/bin/bash

set -e

[ "xxx$1" != "xxx" ] && version=":$1"

bash -c "$(docker run --rm daocloud.io/daocloud/dce${version} install)"
