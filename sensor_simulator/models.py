import random
import globals
import queue
import requests
import json
import sys

class Gateway:
    id = 1
    
    def generate_id():
        newId = Gateway.id
        Gateway.id += 1
        return newId
    
    def __init__(self, interval):
        """
            Args:
                interval : Time between readouts of the sensor values.
        """
        self.id = Gateway.generate_id()
        self.sensors = []
        self.readings = queue.Queue()
        self.nReadings = 0
        self.installation_id = 0
        self.company_id = 0
        self.interval = interval
        
        self.config = ""

        globals.scheduler.add_job(self.transmit, 'interval', seconds=5)
        globals.scheduler.add_job(self.do_readings, 'interval', seconds=self.interval)
    
    
    def add_sensor(self, sensor, save=True):
        sensor.gateway = self
        self.sensors.append(sensor)
        
    def transmit(self):
        """
        Posts all readings in the queue to the REST API.
        """
        while not self.readings.empty():
            reading = self.readings.get()
            
            values = {
                0 : reading.cap, 
                1 : reading.temp1,
                2 : reading.temp2, 
                3 : reading.humidity
            }
            
            payload = {
                'measurements' : []
            }
            for type,value in values.items():
                readingPayload = {
                    "timestamp" : reading.timestamp.isoformat(), #"2015-01-01T00:00:00"
                    "sensor_id" : reading.sensor.id,
                    "measurement_type" : type,
                    "value" : "{:.5f}".format(value) #JSON doesn't do native decimals. Encode as string instead.
                }
                payload['measurements'].append(readingPayload)

            url = "http://localhost:8000/rest/gateways/{}/sensors/{}/measurements/".format(self.id,reading.sensor.id)
            
            try:
                r = requests.post(url, json=payload)
            except requests.exceptions.ConnectionError:
                sys.stderr.write('Failed to make Connection')
            #self.fetch_configuration()
                
    def fetch_configuration(self):
        url = "http://localhost:8000/rest/gateways/{}/config".format(self.id)
        r = requests.get(url)
        print(r)
    
    def do_readings(self):
        """
        Asks each sensor in this gateway for a new reading.
        """
        for sensor in self.sensors:
            sensor.read_out()


class Sensor:
    id = 1
    
    def generate_id():
        newId = Sensor.id 
        Sensor.id += 1
        return newId
    
    def __init__(self):
        self.id = Sensor.generate_id()
        self.counter = 0
        self.currentReading = Reading(0, self)
    
    def read_out(self):
        """
        Takes a new reading and pushes it to the readings-Queue of the gateway 
        for later transmission.
        """
        reading = Reading(self.counter, self, self.currentReading)
        self.currentReading = reading
        self.gateway.readings.put(reading)
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
            self.temp1 = previousReading.temp1 + (random.random() - 0.5)
            self.temp2 = previousReading.temp2 + (random.random() - 0.5)
            self.humidity = previousReading.humidity + (random.random() - 0.5)
            self.cap = previousReading.cap + (random.random() - 0.5)
