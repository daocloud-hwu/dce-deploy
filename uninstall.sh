#!/bin/bash
set -e
conf_file=${1:-dce.conf}

function uninstall_controller_node() {
  #statements
  for i in 1 2 3;
  do
      if [ -n "$(sed -n $i'p' $conf_file)" ];
      then
          echo "start uninstall DCE controller node "$i
          host=`sed -n $i"p" $conf_file | awk '{print $1}'`
          username=`sed -n $i"p" $conf_file | awk '{print $2}'`
          password=`sed -n $i"p" $conf_file | awk '{print $3}'`
          # echo $host $username $password
          # set_nopasswd_login `sed -n $i"p" $conf_file`
          # scp -i ./tmp/dce.rsa setup-dce.sh $username@$host:/root
          ssh -t -i ./tmp/dce.rsa $username@$host bash -c 'echo ----------------;docker stop `docker ps -aq`;docker rm -vf `docker ps -aq`;rm -rf /var/local/dce;rm -rf /etc/daocloud;rm -rf /etc/docker'
      else
          echo "=================================="
          echo "DCE controller uninstall completed"
          echo "=================================="
          break
      fi
  done
}
function uninstall_compute_node() {
  echo "waitting...."
}
function uninstall_dce(){
    uninstall_controller_node
    uninstall_compute_node
}

uninstall_dce
