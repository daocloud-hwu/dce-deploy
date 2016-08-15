#!/bin/bash
function dd(){
    echo $1
    echo $2
    echo $3
}

dd `sed -n 1p dce.conf`
