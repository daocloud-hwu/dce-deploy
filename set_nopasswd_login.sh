#!/bin/sh
host=$1
username=${2:-root}
password=${3:-''}

./set_nopasswd_login.exp $host $username $password
