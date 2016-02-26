"""
Sensor Node Simulator
Usage example: python ./simulator.py --sensors 2 --interval 5

Options:
    --sensors : Number of sensors in each gateway.
    --interval : Clock speed
"""

import time
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler
import sys
import getopt
import json
from virtual_date import *
from models import *
import globals


start_time = time.time()
# Start Scheduler
scheduler = BackgroundScheduler(timezone=utc)
globals.scheduler = scheduler
scheduler.start()

# Retrieve command line arguments.
options = {
    #Default Options
    "nSensors" : 100,
    "interval" : 10, # in s. Equal to 1h in real time.
    "readFromFile" : False,
    "saveToFile" : False,
    "file" : ""
}

try:
    opts, args = getopt.getopt(sys.argv[1:], "s:i:c:",
                               ["sensors=", "installations=",
                                "companies=", "interval=",
                                "gateways=", "clear-db",
                                "load=", "save=",
                                "time="])
    for opt, arg in opts:
        if opt in ('-s', '--sensors'):
            options['nSensors'] = int(arg)
        elif opt in ('-i', '--interval'):
            options['interval'] = float(arg)
        elif opt in ('--load'):
            options['readFromFile'] = True
            options['file'] = arg
        elif opt in ('--save'):
            options['saveToFile'] = True
            options['file'] = arg
        elif opt in ('--time'):
            # options['time'] = arg
            dt = datetime.strptime(arg, '%Y-%m-%d-%H:%M:%S')
            globals.virtualDate.value = int(dt.strftime("%s"))
except getopt.GetoptError:
    print("GETOPT error")

# Initialize clock
print("Current Timestamp {}".format(globals.virtualDate.get_timestamp()))
scheduler.add_job(globals.virtualDate.tick, 'interval', seconds=options['interval'])

print("# of Sensors:  {}".format(options['nSensors']))
print("Sensor Interval: {}s".format(options['interval']))
print("Gateway Interval: {}s".format(10))


# Start new run
print("Bringing Sensors Online")

gateway =  Gateway(options['interval'])
for i in range(1, options['nSensors']+1):
    sensor = Sensor()
    gateway.add_sensor(sensor)


print("\rAll Sensors Online!")
print("\n")

print('Press Ctrl+C to exit')

try:
    while True:
        time.sleep(0.5)
        totalMeasurements = gateway.nReadings
        
        nSecondsInYear = 60*60*24*365
        
        print("\r{} Total Measurements sent to database: {} | Simulation Time: {}h = {:.5f}y.".format(
                                                    globals.virtualDate.get_timestamp(), 
                                                    totalMeasurements,
                                                    globals.virtualDate.get_time_elapsed() / (60*60), 
                                                    globals.virtualDate.get_time_elapsed() / nSecondsInYear
                                                ),
                                                end=""
        )
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
finally:
    print("")
    print("GoodBye!")
