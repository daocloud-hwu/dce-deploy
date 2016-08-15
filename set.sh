#!/bin/bash
set -e
conf_file=${1:-dce.conf}

#functon list
#Parameter: x.x.x.x username password
function set_nopasswd_login()
{
    echo "host is $1"
    echo "username is $2"
    echo "password is $3"
    if [ -n $1 ] && [ -n $2 ] && [ -n $3 ];
    then
        ./set_nopasswd_login.sh $1 $2 $3
    else
        echo "you need to use root user to login"
        exit 1
    fi
}
function load_cluster_config_file() {
  #statements
  #load host conf file
  if [ ! -z "$conf_file" ] && [ -f $conf_file ];
  then
      echo "loading configure file:" $conf_file
  else
      echo "can't find configure file"
      exit 1
  fi
  #init generate sra file
  if [ ! -f ./tmp/dce.rsa ] && [ ! -f ./tmp/dce.rsa.pub ];
  then
      ssh-keygen -P '' -f ./tmp/dce.rsa
  else
      echo "rsa file has been generated"
  fi
}
function init_config() {
  #statements
  load_cluster_config_file
}
function setup_controller_node() {
  #statements
  for i in 1 2 3;
  do
      if [ -n "$(sed -n $i'p' $conf_file)" ];
      then
          echo "start set up DCE controller node "$i
          host=`sed -n $i"p" $conf_file | awk '{print $1}'`
          username=`sed -n $i"p" $conf_file | awk '{print $2}'`
          password=`sed -n $i"p" $conf_file | awk '{print $3}'`
          # echo $host $username $password
          set_nopasswd_login `sed -n $i"p" $conf_file`
          scp -i ./tmp/dce.rsa setup-dce.sh $username@$host:/root
          ssh -t -i ./tmp/dce.rsa $username@$host bash -c '/root/setup-dce.sh'
      else
          echo "=============================="
          echo "DCE controller setup completed"
          echo "=============================="
          break
      fi
  done
}
function setup_compute_node() {
  echo "waitting...."
}
function setup_dce(){
    setup_controller_node
    setup_compute_node
}
function configure_dce() {
  #statements
  # $user=admin
  # $Password=admin
  curl -H "Content-Type: application/json" -X PATCH http://$host/api/settings/auth -d '{"Method": "managed"}'
  curl -X POST -H "Content-Type: application/json" -d '{"Name": "admin","Email": "admin2@cc.com",  "IsAdmin": true,"Password": "admin"}' "http://$host/api/v1/accounts"
}

init_config
setup_dce
configure_dce `sed -n 1p $conf_file | awk '{print $1}'`
