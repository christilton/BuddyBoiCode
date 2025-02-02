import uasyncio as asyncio
from machine import I2C, Pin
import adafruit_sht4x

async def main():
    # Initialize I2C bus

    # Initialize SHT4x sensor
    sht = adafruit_sht4x.SHT4x(20, 21)

    # Read temperature and humidity asynchronously
    while True:
        temperature = sht.temperature
        humidity = sht.relative_humidity

        print("Temperature: {}°C, Humidity: {}%".format(temperature, humidity))

        await asyncio.sleep(2)  # Read every 2 seconds

# Run the asyncio event loop
asyncio.run(main())

