import random
import globals
import queue
import requests
import sys


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

        self.readingsFailed = []
        self.readingsSuccess = []
    
    def add_sensor(self, sensor, save=True):
        sensor.gateway = self
        self.sensors.append(sensor)
        
    def transmit(self):
        """
        Posts all readings in the queue to the REST API.

        The measurement data is packed for each sensor.
        This means that the gateway will send all measurements for a sensor in one request.
        The total number of requests per transmission for the entire installation is: #gateways x #sensors.

        To ensure that the connection is up the gateway will first try a get request
        on it's own REST resource. (/gateways/$ID)
        If that fails the current transmission will not be started. The readings remain thus in
        the list of their respective sensor.

        Payload has the following format:
        {
            "measurements" : [


            ]
        }
        """
        print("Probe Connection")

        if self.probe():
            print("Begin Transmission.")

            # First try to transmit previously failed readings again.
            for reading in self.readingsFailed[:]:
                payload = {
                    'measurements' : []
                }

                payload_partial = self.preparePayload(reading)
                payload['measurements'].append(payload_partial)

                try:
                    url = globals.server["host"] + "/gateways/{}/sensors/{}/measurements/".format(self.id, reading.sensor.id)
                    r = requests.post(url, json=payload, verify=False)

                    # Reaching this code means that the transmission was successful
                    self.readingsSuccess.append(reading)
                    self.readingsFailed.remove(reading)
                except requests.exceptions.ConnectionError:
                    pass

            for sensor in self.sensors:
                # Pack all measurements together.
                payload = {
                    'measurements' : []
                }

                readingCachedList = []

                counter = 20
                while not sensor.readings.empty() and counter >= 0:
                    counter -= 1

                    # Reading removed from list!
                    reading = sensor.readings.get()
                    readingCachedList.append(reading) # Store in temporary list.

                    payload_partial = self.preparePayload(reading)
                    payload['measurements'].extend(payload_partial)

                try:
                    url = globals.server["host"] + "/gateways/{}/sensors/{}/measurements/".format(self.id, sensor.id)
                    #print(payload)


                    # pp = pprint.PrettyPrinter(indent=4)
                    # pp.pprint(payload)

                    r = requests.post(url, json=payload, verify=False)

                    # Reaching this code means that the transmission was successful

                    for reading in readingCachedList:
                        # Move readings to success list.
                        self.readingsSuccess.append(reading)
                    readingCachedList.clear()
                except requests.exceptions.ConnectionError:
                    # Despite the check at the beginning of the transmission, it is still possible that the request
                    # fails.
                    for reading in readingCachedList:
                        # Move readings to failed list.
                        self.readingsFailed.append(reading)
                    readingCachedList.clear()
                    sys.stderr.write('Failed to make Connection')
            print("End Transmission.")

    def probe(self):
        """
            Connects to the server and returns a boolean indicating whether it was successful or not.

            Returns:
                True when connection succeeded.
                False when a connection error, or an HTTP error code was received.
        """
        success = False
        try:
            url = globals.server["host"] + "/gateways/{}.json".format(self.id)
            r = requests.get(url, verify=False)
            if r.status_code == requests.codes.ok:
                success = True
        except requests.exceptions.ConnectionError:
            pass
        return success

    def preparePayload(self, reading):
        """

            Args:
                readings : List of readings.
            Returns:
                A string containing the JSON data to form the POST request.
        """
        payload = []
        values = {
                    1 : reading.cap,
                    2 : reading.temp1,
                    3 : reading.temp2,
                    4 : reading.humidity
                }

        for type,value in values.items():
            readingPayload = {
                "timestamp" : reading.timestamp.isoformat(), #"2015-01-01T00:00:00"
                "sensor_id" : reading.sensor.id,
                "measurement_type" : type,
                "value" : float("{0:.5f}".format(value))
            }
            payload.append(readingPayload)

        return payload



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

    def __str__(self):
        # 1 : reading.cap,
        # 2 : reading.temp1,
        # 3 : reading.temp2,
        # 4 : reading.humidity

        # MeasurementTypeID, sensor_id, timestamp, value
        timestamp = self.timestamp.strftime("%Y-%m-%dT%H:%M:%S")
        str = "1 {} {} {}\n".format(self.sensor.id, timestamp, float("{0:.5f}".format(self.cap)))
        str += "2 {} {} {}\n".format(self.sensor.id, timestamp, float("{0:.5f}".format(self.temp1)))
        str += "3 {} {} {}\n".format(self.sensor.id, timestamp, float("{0:.5f}".format(self.temp2)))
        str += "4 {} {} {}\n".format(self.sensor.id, timestamp, float("{0:.5f}".format(self.humidity)))
        return str
