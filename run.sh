#!/bin/bash
# Launches multiple gateways using the simulator.py program.
pids[0]=''

for N in {0..2}
do
    echo "Launching gateway $N"
    python sensor_simulator/simulator.py --gateway-id 1 --interval 60 > /dev/null &
    pids[$N]=$! # Store Process ID in array.
    sleep 10s
done

sleep 30m

echo "Killing ${pids[@]}"
kill -s SIGINT ${pids[@]}