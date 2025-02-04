import uasyncio as asyncio
import machine
from machine import I2C, Pin, WDT
import urequests as requests
import time, sys
from gc import collect as gc
from secrets import ADAFRUIT_AIO_KEY, ADAFRUIT_AIO_USERNAME, ssid, password
import getSunriseSunset as gss

# Assuming you have the adafruit_sht4x library for MicroPython
from adafruit_sht4x import SHT4x
import network

# Global variable for setpoint
setpoint = 0
deadband = .25

sunHasRisen = False
sunHasSet = False

connected = False

current_timestamp = 0

hungryGecko = WDT(timeout=300000) #5 minute timeout
    
# Initialize relay pin
relay = Pin(4, Pin.OUT)
sht = None

# I2C configuration for controlling NeoPixels
SDA_PIN = 0  # Adjust pins as necessary
SCL_PIN = 1
trinket = I2C(0,scl=Pin(SCL_PIN, Pin.PULL_UP), sda=Pin(SDA_PIN, Pin.PULL_UP))
resetpin = Pin(2, Pin.OUT)
resetpin.high()
    
#button_pin = Pin(15, Pin.IN)

def reset_i2c():
    global i2c
    i2c = I2C(1, scl=Pin(19), sda=Pin(18))  # Reinitialize I2C
    print("I2C Reset")

# Address of the Arduino Pro Trinket (Worker)
TRINKET_ADDRESS = 0x12  # Example address

# Function to send RGB color to the Trinket
def send_color(lighttype,r, g, b,brightness):
    color_data = bytearray([lighttype,r, g, b,brightness])
    while True:
        try:
            trinket.writeto(TRINKET_ADDRESS, color_data)
            break
        except OSError as e:
            print(f"Error sending color: {e}")
            time.sleep(5)
            continue


def reset_trinket():
    resetpin.low()
    time.sleep(.1)
    resetpin.high()
    time.sleep(.1)

# Colors for daytime and off
DAY_COLOR = (1,255, 150, 20,255)  # Golden Yellow
OFF_COLOR = (1, 0, 0, 0, 0)        # Off

async def update_setpoint_feed(new_setpoint):
    global setpoint
    FEED_KEY = 'setpoint-gecko'
    url = f'https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/{FEED_KEY}/data'
    
    data = {'value': new_setpoint}
    headers = {
        'X-AIO-Key': ADAFRUIT_AIO_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        gc()
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            print(f"Successfully updated setpoint feed.")
        else:
            print(response.text)
        response.close()
    except Exception as e:
        print(f"Failed to update setpoint feed: {e}")
        
    await asyncio.sleep(900)

async def manage_setpoint():
    global setpoint
    global current_timestamp
    while True:
        url = f'https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/day-setpoint-gecko/data/last'
        headers = {
        'X-AIO-Key': ADAFRUIT_AIO_KEY,
        'Content-Type': 'application/json'
        }
        gc()
        if connected:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                #print(data)
                daytime_setpoint = float(data['value'])
                response.close()
            else:
                daytime_setpoint = 69.0 #HARDCODE HERE
        else:
            daytime_setpoint = 69.0 #HARDCODE HERE
        url = f'https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/night-setpoint-gecko/data/last'
        headers = {
        'X-AIO-Key': ADAFRUIT_AIO_KEY,
        'Content-Type': 'application/json'
        }
        gc()
        if connected:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                nighttime_setpoint = float(data['value'])
            else:
                nighttime_setpoint = 64.0 #HARDCODE HERE
        else:
            nighttime_setpoint = 64.0
        response.close()
        
        #HANDLE TIME HERE
        if connected:
            new_setpoint = nighttime_setpoint if compare_timestamps(current_timestamp, sunset,1800) or not compare_timestamps(current_timestamp, sunrise,3600) else daytime_setpoint
        else:
            new_setpoint = 67.0
        
        if setpoint != new_setpoint:
            setpoint = new_setpoint
            print(f"Setpoint changed to: {setpoint}°F")
            await update_setpoint_feed(setpoint)
        
        await asyncio.sleep(90)  # Check every minute     

async def read_sensor(sht):
    lamp_status = 0
    max_retries = 5
    while True:
        retries = 0
        while retries < max_retries:
            try:
                temperature = round(sht.temperature, 2)
                humidity = round(sht.relative_humidity, 2)
                break  # Successful read, exit retry loop
            except OSError as e:
                if "CRC" in str(e):
                    print("CRC error detected, retrying...")
                else:
                    print(f"Sensor read error: {e}")
                retries += 1
                await asyncio.sleep(0.5)  # Small delay before retry
        else:
            print("Max retries reached, skipping this cycle.")
            await send_status_notification("CRC Error. Resetting...")
            reset_trinket()
            machine.reset()
            # Skip to next loop iteration
        #print("Temperature: {}°F, Humidity: {}%".format(temperature, humidity))

        # Bang-bang controller logic
        if temperature < setpoint - deadband:
            relay.on()  # Turn on the heat lamp
            if lamp_status == 0 :
                if connected:
                    data = {'value': 'ON'}
                    FEED_KEY = 'lamp-gecko'
                    url = f'https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/{FEED_KEY}/data'
                    headers = {
                        'X-AIO-Key': ADAFRUIT_AIO_KEY,
                        'Content-Type': 'application/json'
                    }
                    reply = requests.post(url, headers=headers, json=data)
                    reply.close()
                lamp_status = 1
                print("Heat Lamp turned ON.")
    
        elif temperature > setpoint:
            relay.off()  # Turn off the heat lamp
            if lamp_status == 1:
                if connected:
                    data = {'value': 'OFF'}
                    FEED_KEY = 'lamp-gecko'
                    url = f'https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/{FEED_KEY}/data'
                    headers = {
                        'X-AIO-Key': ADAFRUIT_AIO_KEY,
                        'Content-Type': 'application/json'
                    }
                    reply = requests.post(url, headers=headers, json=data)
                    reply.close()

                lamp_status = 0
                print("Heat Lamp turned OFF.")
    
        await asyncio.sleep(1)  # Read sensor values every second

async def send_temp():
    if connected:
        FEED_KEY = 'temperature-gecko'
        url = f'https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/{FEED_KEY}/data'
        global current_timestamp
        
        while True:
            if sht is not None:
                if sht.temperature is not None:
                    temperature = round(sht.temperature, 2) 
            data = {'value': temperature}
            headers = {
                'X-AIO-Key': ADAFRUIT_AIO_KEY,
                'Content-Type': 'application/json'
            }
            
            try:
                # Send data to Adafruit IO
                gc()
                reply = requests.post(url, headers=headers, json=data)
                #print(reply.text)
                data = reply.json()
                timestamp_str = data['created_at']
                #print(timestamp_str)
                sse = time.mktime(gss.GetTimeTuple(timestamp_str)) # type: ignore
                current_timestamp = gss.GetTimeStamp((time.localtime(sse+(offset*60))))
                
                #print(f"Current Time: {current_timestamp} ET")
                if reply.status_code != 200:
                    print(reply.status_code)
                    print(reply.text)
                reply.close()  # Close the response to free up resources
            except Exception as e:
                print("Failed to send data (T):", e)
            
            await asyncio.sleep(10)  # Send data every 10 seconds

async def send_humidity():
    if connected:
        FEED_KEY = 'humidity-gecko'
        url = f'https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/{FEED_KEY}/data'
        
        while True:
            if sht is not None:
                if sht.relative_humidity is not None:
                    humidity = round(sht.relative_humidity, 2)
            
            data = {'value': humidity}
            headers = {
                'X-AIO-Key': ADAFRUIT_AIO_KEY,
                'Content-Type': 'application/json'
            }
            
            try:
                # Send data to Adafruit IO
                gc()
                reply = requests.post(url, headers=headers, json=data)
                if reply.status_code != 200:
                    print(reply.status_code)
                    print(reply.text)
                reply.close()  # Close the response to free up resources
            except Exception as e:
                print("Failed to send data: (H)", e)
            
            await asyncio.sleep(10)  # Send data every 10 seconds
        
async def control_neopixels():
    global current_timestamp, sunHasRisen, sunHasSet

    sunrise_duration = 3600  # Duration: 1 hour (3600 seconds)
    sunset_duration = 3600   # Duration: 1 hour (3600 seconds)
    sunrise_steps = 50       # Number of steps for sunrise
    sunset_steps = 50        # Number of steps for sunset
    if connected:
        while True and connected:
            state = 0
            last_state = 0
            if not sunHasRisen and not sunHasSet:
                mode = 'Sunrise'
            else:
                mode = 'Sunset'
            if compare_timestamps(current_timestamp, sunrise, 0) and not compare_timestamps(current_timestamp,sunset,3600):
                send_color(*DAY_COLOR)
                state = 1
                sunHasRisen = True
            elif compare_timestamps(current_timestamp, sunrise, 900) and not compare_timestamps(current_timestamp,sunset, 2700):
                state = 2
                send_color(1,255,150,20,191)
            elif compare_timestamps(current_timestamp, sunrise, 1800) and not compare_timestamps(current_timestamp,sunset,1800):
                send_color(1,255,150,20,127)
            elif compare_timestamps(current_timestamp, sunrise, 2700) and not compare_timestamps(current_timestamp,sunset,900):
                send_color(1,255,150,20,63)
            else:
                await send_status_notification("Nighttime Mode, Lights off")
                send_color(*OFF_COLOR)
                sunHasSet = True
            #status for lights only sends when state changes
            if last_state != state:
                if state == 1:
                    await send_status_notification("Daytime Mode, Lights on FULL BRIGHTNESS")
                    last_state = 1
                elif state == 2:
                    await send_status_notification(f"{mode} Mode, Lights on 75% BRIGHTNESS")
                    last_state = 2
                elif state == 3:
                    await send_status_notification(f"{mode} Mode, Lights on 50% BRIGHTNESS")
                    last_state = 3
                elif state == 4:
                    await send_status_notification(f"{mode} Mode, Lights on 25% BRIGHTNESS")
                    last_state = 4
            await asyncio.sleep(60)
    else: 
        send_color(*OFF_COLOR)

            

async def send_status_notification(message):
    if connected:
        FEED_KEY = 'status-gecko'
        url = f'https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/{FEED_KEY}/data'
        data = {'value': str(message)}
        headers = {
            'X-AIO-Key': ADAFRUIT_AIO_KEY,
            'Content-Type': 'application/json'
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            response.close()
        except Exception as e:
            print(f"Failed to send error notification: {e}")

async def check_reboot(upday):
    if connected:
        while True:
            current_day = gss.GetDay()
            print(f'upday = {upday}, current_day = {current_day}')
            await send_status_notification(f'Checking Reboot: upday = {upday}, current_day = {current_day}')
            
            if current_day is None:
                print("Error: Unable to fetch current day")
                await send_status_notification("System unable to verify date, skipping reboot check.")
                return  # Skip reboot check if we can't get the date

            if current_day != upday:
                await send_status_notification("System Resetting")
                relay.off()
                reset_trinket()
                machine.reset()
                
            await asyncio.sleep(900)

async def watchGecko():
    while True:
        hungryGecko.feed()
        await asyncio.sleep(10)


async def check_connection(wlan):
    global connected
    while True:
        if not wlan.isconnected():
            print("Wi-Fi disconnected! Attempting to reconnect...")
            send_color(59, 255, 255, 255, 100)  # White = Reconnecting
            wlan.disconnect()
            time.sleep(2)
            new_wlan = connectWifi()
            if new_wlan:
                wlan = new_wlan  # Update reference if reconnected
                connected = True
            else:
                connected = False
        else:
            connected = True
        await asyncio.sleep(60)  # Check every minute
    

        
def connectWifi():
    global connected 
    send_color(59, 255,255,255,100)  # Indicate connection attempt
    print('Attempting to Connect to WiFi...')
    
    station = network.WLAN(network.STA_IF)
    station.active(True)
    station.connect(ssid, password)
    
    timeout = 0
    while not station.isconnected() and timeout < 100:  # 10-second timeout
        time.sleep(0.1)
        timeout += 1

    if station.isconnected():
        connected = True
        send_color(59, 0,255,0,100)  # Green = success
        print(f'Connected to {ssid}.')
        asyncio.run(send_status_notification(f"Connected to {ssid}"))
        return station
    else:
        connected = False
        send_color(59, 255,0,0,100)  # Red = failure
        return None


def compare_timestamps(currenttime,eventtime,newoffset):
    ct = time.mktime(gss.GetTimeTuple(currenttime))-newoffset # type: ignore
    et = time.mktime(gss.GetTimeTuple(eventtime))-newoffset # type: ignore
    if int(ct) >= int(et):
        return True
    else:
        return False

    
async def main():
    # Start the tasks
    try:
        await asyncio.gather(
            read_sensor(sht),
            send_temp(),
            send_humidity(),
            manage_setpoint(),
            control_neopixels(),
            check_reboot(upday),
            check_connection(wlan),
            watchGecko()
            #button_checker(),
            #manage_pump()
        ) # type: ignore
    except Exception as e:
        relay.off()
        print(f"Exception occurred: {e}")
        send_color(2,1,1,1,255)
        await send_status_notification(e)
        reset_trinket()
        machine.reset()

# Run the asyncio event loop
try:
    reset_trinket()
    time.sleep(3)
    wlan = connectWifi()
    print("Inizializing...")
    send_color(58,255,255,255,100)
    retries = 0
    while retries < 5:
        try:
            sht = SHT4x(1,18,19)
            if sht is not None:
                asyncio.run(send_status_notification("Temperature Sensor Connected, System Starting"))
                send_color(58,0,255,0,100)
                break
            else:
                retries+= 1
        except OSError as e:
            print(f"Error: {e}")
            send_color(58,255,0,0,100)
            retries += 1
            time.sleep(1)
            continue
    send_color(57,255,255,255,100)
    if connected:
        offset,sunrise,sunset = gss.GetSunriseSunset()
        upday = gss.GetDay()
        uptime2 = gss.GetTime()
        uptime2_timestamp = gss.GetTimeStamp(time.localtime(uptime2))
        asyncio.run(send_status_notification(f"Uptime Date: {uptime2_timestamp}, Upday: {upday}, Sunrise = {sunrise}, Sunset = {sunset}"))
    if compare_timestamps(uptime2_timestamp,sunrise,0):
        sunHasRisen = True
    if compare_timestamps(uptime2_timestamp,sunset,0):
        sunHasSet = True
    print(f"Risen: {sunHasRisen}, Set: {sunHasSet}")
    send_color(57,0,255,0,100)
    asyncio.run(send_status_notification("Initialization complete, System ON"))
    time.sleep(2)
    send_color(1,0,0,0,0)
    #MAIN LOOP
    asyncio.run(main())
except KeyboardInterrupt:
    print("System Stopped")
    relay.off()
    send_color(1,0,0,0,0)
    asyncio.run(send_status_notification("System Stopped by Keyboard Interrupt"))
except Exception as e:
    print(f"System Error: {e}")
    relay.off()
    send_color(1,0,0,0,0)
    time.sleep(.01)
    send_color(2,255,1,1,1)
    asyncio.run(send_status_notification(f"System Stopped by Exception: {e}"))
    reset_trinket()
    machine.reset()