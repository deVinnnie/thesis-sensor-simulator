import random
import globals
import queue
import requests
import json
import sys
import pprint

class Gateway:
    def __init__(self, interval, sensorInterval, id):
        """
            Args:
                interval : Time between transmissions of the readings to the server.
                sensorInterval : Time between readouts of the sensor values.
                id : Unique identifier for this gateway instance. Must be the same as in the database.
        """
        self.id = id
        self.sensors = []

        self.nReadings = 0
        self.interval = interval
        self.sensorInterval = sensorInterval

        self.config = ""

        globals.scheduler.add_job(self.transmit, 'interval', seconds=self.interval)
        globals.scheduler.add_job(self.do_readings, 'interval', seconds=self.sensorInterval)
    
    
    def add_sensor(self, sensor, save=True):
        sensor.gateway = self
        self.sensors.append(sensor)
        
    def transmit(self):
        """
        Posts all readings in the queue to the REST API.

        Number of requests = #sensors
        """
        print("Begin Transmission.")
        for sensor in self.sensors:
            # Pack all measurements together.
            payload = {
                    'measurements' : []
                    }

            # Payload:
            # "measurements" : [
            #     [ "20150101",  ],
            #     [],
            # ]

            counter = 5
            while not sensor.readings.empty() and counter >= 0:
                counter -= 1
                reading = sensor.readings.get()
                values = {
                    0 : reading.cap,
                    1 : reading.temp1,
                    2 : reading.temp2,
                    3 : reading.humidity
                }

                for type,value in values.items():
                    readingPayload = {
                        "timestamp" : reading.timestamp.isoformat(), #"2015-01-01T00:00:00"
                        "sensor_id" : reading.sensor.id,
                        "measurement_type" : type,
                        "value" : float("{0:.5f}".format(value))
                    }
                    payload['measurements'].append(readingPayload)

            # pp = pprint.PrettyPrinter(indent=4)
            # pp.pprint(payload)

            url = globals.server["host"] + "/gateways/{}/sensors/{}/measurements/".format(self.id, sensor.id)
            try:
                r = requests.post(url, json=payload, verify=False)
            except requests.exceptions.ConnectionError:
                sys.stderr.write('Failed to make Connection')
        print("End Transmission.")
                
    def fetch_configuration(self):
        url = globals.server["host"] + "/gateways/{}/config".format(self.id)
        r = requests.get(url)
        print(r)
    
    def do_readings(self):
        """
        Asks each sensor in this gateway for a new reading.
        """
        for sensor in self.sensors:
            sensor.read_out()


class Sensor:
    def __init__(self, id=None):
        self.id = id
        self.counter = 0
        self.currentReading = Reading(0, self)
        self.readings = queue.Queue()
    
    def read_out(self):
        """
        Takes a new reading and pushes it to the readings-Queue of this sensor
        for later transmission.
        """
        reading = Reading(self.counter, self, self.currentReading)
        self.currentReading = reading
        self.readings.put(reading)
        self.counter += 1


class Reading:
    def __init__(self, id, sensor, previousReading=None):
        self.reading_id = id
        self.sensor = sensor
        self.timestamp = globals.virtualDate.get_timestamp()

        if previousReading is None:
            self.temp1 = 20.0
            self.temp2 = 20.0
            self.humidity = 0.4118
            self.cap = 1.0
        else:
            # Increase measurements by a random value in the range of -0.5 to +0.5.
            self.temp1 = previousReading.temp1 + (random.random() - 0.5)
            self.temp2 = previousReading.temp2 + (random.random() - 0.5)
            self.humidity = previousReading.humidity + (random.random() - 0.5)
            self.cap = previousReading.cap + (random.random() - 0.5)
