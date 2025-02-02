#connectWifi

import network
import time
import ubinascii
from secrets import ssid, password

station = network.WLAN(network.STA_IF)
station.active(True)

scan = False

if scan == True:
    mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
    print(mac)
    print("Scanning...")
    for _ in range(2):
        scan_result = station.scan()
        for ap in scan_result:
            print("SSID:%s BSSID:%s Channel:%d Strength:%d RSSI:%d Auth:%d "%(ap))
        print()
        time.sleep_ms(1000)
        

station.connect(ssid, password)
while station.isconnected() == False:
    time.sleep(1)
    pass
print(f'Connected to {ssid}.')
#print(station.ifconfig())

