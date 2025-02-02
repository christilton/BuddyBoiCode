import uasyncio as asyncio
from machine import I2C, Pin
import urequests as requests
from secrets import ADAFRUIT_AIO_KEY, ADAFRUIT_AIO_USERNAME
import connectWifi

# Assuming you have the adafruit_sht4x library for MicroPython
from adafruit_sht4x import SHT4x

# Set the temperature thresholds for the bang-bang controller
TARGET_TEMPERATURE = 72.0  # Target temperature in °F
DEADBAND = 0.5  # Temperature deadband in °F

# Initialize the relay pin (connected to GPIO 4)
relay = Pin(4, Pin.OUT)
sht = SHT4x(20,21)

async def read_sensor(sht):
    while True:
        temperature = round(sht.temperature, 2)
        humidity = round(sht.relative_humidity, 2)
        
        print("Temperature: {}°F, Humidity: {}%".format(temperature, humidity))
        
        # Bang-bang controller logic
        if temperature < TARGET_TEMPERATURE - DEADBAND:
            relay.on()  # Turn on the heat lamp
            print("Heat lamp ON")
        elif temperature > TARGET_TEMPERATURE + DEADBAND:
            relay.off()  # Turn off the heat lamp
            print("Heat lamp OFF")
        
        await asyncio.sleep(1)  # Read sensor values every second

async def send_data():
    FEED_KEY = 'temperature-gecko'
    url = 'https://io.adafruit.com/api/v2/%s/feeds/%s/data' % (ADAFRUIT_AIO_USERNAME, FEED_KEY)
    
    while True:
        temperature = round(sht.temperature, 2)
        
        data = {'value': temperature}
        headers = {
            'X-AIO-Key': ADAFRUIT_AIO_KEY,
            'Content-Type': 'application/json'
        }
        
        try:
            # Send data to Adafruit IO
            reply = requests.post(url, headers=headers, json=data)
            if reply.status_code != 200:
                print(reply.status_code)
                print(reply.text)
            reply.close()  # Close the response to free up resources
        except Exception as e:
            print("Failed to send data:", e)
        
        await asyncio.sleep(10)  # Send data every 10 seconds

async def main():
    # Start the sensor reading and data sending tasks
    await asyncio.gather(read_sensor(sht), send_data())

# Run the asyncio event loop
asyncio.run(main())

