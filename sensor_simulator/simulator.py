"""
Sensor Node Simulator
Usage example: python ./simulator.py --sensors 2 --interval 5

Options:
    --sensors : Number of sensors in the gateway.
                Only used for creating a new gateway. When the gateway already exists the number of sensors will be
                loaded via the REST api.
    --interval : Clock speed. One interval is equal to 2 hours of simulation time.
                 We suppose that a measurement happens every 2 hours.
    --gateway-id : Unique ID assigned to the gateway (has to exist on the server).
                   If the gateway doesn't exist yet the program exits.
    
    --installation-id : Unique ID of the parent installation for a new gateway. 
                        A new gateway is created under the specified installation.
                        Only specify either installation-id or gateway-id.
                        For the new gateway a id is assigned by the server.


The program writes out a file with all measurements transmitted to the server. This happens at the end of the run, after
receiving the SIGINT signal. Only measurements processed by the gateway will be included.
Measurements still stored in the sensor's queue will not be considered.
"""

import time
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler
import sys
import argparse
from virtual_date import *
from models import *
import globals
import signal


start_time = time.time()

# Start Scheduler
scheduler = BackgroundScheduler(timezone=utc)
globals.scheduler = scheduler
scheduler.start()

# Transmit interval = every day = 24h.
# 2 hours = 5s.
# 12 h = 6*5s = 30s.

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--interval', nargs='?', type=int, help='Update interval', default=5)
parser.add_argument('--gateway-interval', nargs='?', type=int, help='Update interval', default=60, dest='gatewayInterval')
parser.add_argument('--sensors', nargs='?', type=int, help='Number of sensors attached to this gateway.', default=100, dest='nSensors')
parser.add_argument('--gateway-id',nargs='?', type=int, help='Unique ID assigned to the gateway (has to exist on the server).', default=0, dest='gatewayId')
parser.add_argument('--installation-id', nargs='?', type=int, help='ID of the installation for which a new gateway will be created.', default=0, dest='installationId')
options = parser.parse_args()
options.gatewayInterval = 12 * options.interval # The gateway transmits once every day. One interval is 2 hours.

#             # options['time'] = arg
#             dt = datetime.strptime(arg, '%Y-%m-%d-%H:%M:%S')
#             globals.virtualDate.value = int(dt.strftime("%s"))

# Initialize clock
print("Current Timestamp {}".format(globals.virtualDate.get_timestamp()))
print(options.interval)
scheduler.add_job(globals.virtualDate.tick, 'interval', seconds=options.interval)

gateway = None


if options.gatewayId:
    # Gateway already exist.
    # Get the gateway's information via REST and initialize it with the correct number of sensors.
    try:
        print("Retrieving Configuration from Server")
        url = globals.server["host"] + "/gateways/{}.json".format(options.gatewayId)
        r = requests.get(url, verify=False)
        
        if(r.status_code == requests.codes.not_found):
            # Gateway does not exist.
            exit()
        else:
            gateway = Gateway(options.gatewayInterval, options.interval, options.gatewayId)

            # Analyze payload, retrieve sensors.
            response = r.json()
            sensors = response['sensors']

            print("Found {} sensors".format(len(sensors)))
            print("Bringing Sensors Online")
            for s in sensors:
                sensor = Sensor(s['sensor_id'])
                gateway.add_sensor(sensor)
    except requests.exceptions.ConnectionError:
        print('Failed to make Connection')

if options.installationId:
    # Gateway does not yet exist.
    # Make a new one via the REST API and make it a child of the given installation.
    try:
        url = globals.server["host"] + "/gateways/"
        payload = {
            "ip_address": "-",
            "sensors": [],
            "config": [],
            "installation" : options.installationId
        }
        r = requests.post(url, json=payload)

        if(r.status_code == 400):
            print("Installation does not exist!")
            exit()

        response = r.json()
        gateway = Gateway(options.gatewayInterval, options.interval, response['gateway_id'])

        url = globals.server["host"] + "/gateways/{}/sensors/".format(gateway.id)
        for n in range(1,options.nSensors):
            payload = {
                "name": "Sensor Node",
                #"gateway_id": ,
                "config": []
            }

            r = requests.post(url, json=payload)
            response = r.json()

            sensor = Sensor(response['sensor_id'])
            #print("Attaching new sensor with id {}".format(sensor.id))

            gateway.add_sensor(sensor)

    except requests.exceptions.ConnectionError:
        sys.stderr.write('Failed to make Connection')


print("GatewayID: {}".format(options.gatewayId))
print("# of Sensors:  {}".format(options.nSensors))
print("Sensor Interval: {}s".format(options.interval))
print("Gateway Interval: {}s".format(options.gatewayInterval))

# Start new run
print("\n")
print('Press Ctrl+C to exit')


def handler(signum, frame):
    # Will cause the main loop to quit and clean up.
    exit()

# Attach a listener for the SIGINT signal.
# This way the program can exit gracefully when killed using the kill $PID command.
signal.signal(signal.SIGINT, handler)

try:
    nSecondsInYear = 60*60*24*365
    while True:
        time.sleep(0.5)
        totalMeasurements = gateway.nReadings

        # Use \r (carriage return, no line feed) to print over the previous output.
        print("\r{} Total Measurements sent to database: {} | Simulation Time: {}h = {:.5f}y.".format(
                                                    globals.virtualDate.get_timestamp(), 
                                                    totalMeasurements,
                                                    globals.virtualDate.get_time_elapsed() / (60*60), 
                                                    globals.virtualDate.get_time_elapsed() / nSecondsInYear
                                                ),
                                                end=""
        )
except (KeyboardInterrupt, SystemExit):
    pass
finally:
    scheduler.shutdown()
    print("")

    f = open("gateway{}.txt".format(gateway.id), 'w')

    for reading in gateway.readingsSuccess:
        #print(reading)
        f.write(reading.__str__())
    f.close()

    f = open("gateway{}_failed.txt".format(gateway.id), 'w')
    for reading in gateway.readingsFailed:
        #print(reading)
        f.write(reading.__str__())
    f.close()

    print("GoodBye!")
