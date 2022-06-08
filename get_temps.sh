#!/bin/bash

# Get names on OneWire-Bus and read all temperatures
wd="/home/pi/heizungsmonitor"


now=$(date +"%Y-%m-%d--%H-%M-%S")
filename=$(printf "%s/%s.txt" $wd `date +"%Y-%m-%d"`)

# read devices and store their names in an array
devices=(`find /sys/devices/w1_bus_master1/ -name "w1_slave"`)

# loop over files and write out id with temperature
for d in "${devices[@]}"
do
    # extract device name from path
    id=`awk -F'/' '{print $5}' <<< $d`
    # read temperature and divide by 1000
    T=`tail -1 $d | awk -F'=' '{print $2}'`
    t=`echo "scale=2; $T / 1000.0" | bc`
    # print to stdout
    printf "%s  %s  %s\n" $now $id $t >> $filename
done
