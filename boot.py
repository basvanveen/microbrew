# skip
import network
try:
  import usocket as socket
except:
  import socket
import ntptime
import time
import ujson as json

with open('settings/wireless.json', 'r') as f:
    wirelesscredentials = json.load(f)

UTC_OFFSET = 2 * 60 * 60

sta_if = network.WLAN(network.STA_IF); sta_if.active(True)
sta_if.scan()                             # Scan for available access points
sta_if.connect(wirelesscredentials['SSID'],
               wirelesscredentials['PASSWORD']) # Connect to an AP
sta_if.isconnected()                      # Check for successful connection
time.sleep(2)
ntptime.settime()
