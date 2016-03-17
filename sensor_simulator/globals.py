from virtual_date import *
import time

virtualDate = VirtualDate(int(time.time()))

server = {
    "host" : "https://192.168.1.10:8443/rest",
    "api-key" : "XXXX-XXXX"
}