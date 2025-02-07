import time, machine

class SEN0546:
    """
    A class for the DFRobot SEN0546 Temperature and Humidity Sensor.

    The sensor returns 4 bytes when you write register 0x00:
      - The first two bytes (big‐endian) are the raw temperature reading.
      - The next two bytes (big‐endian) are the raw humidity reading.

    Conversion formulas (as given in the manufacturer’s Arduino code):
      - Temperature in °C:  (raw_temp * 165 / 65535) - 40
      - Temperature in °F:  (temp_C * 9/5) + 32
      - Humidity (%RH):      (raw_humidity / 65535) * 100
    """

    def __init__(self, i2c=None, scl_pin=None, sda_pin=None, freq=100000, address=0x40, swap_bytes=True):
        """
        Initialize the SEN0546 sensor.

        Parameters:
          i2c      -- an existing I2C instance (optional)
          scl_pin  -- the SCL pin number (if no i2c is provided)
          sda_pin  -- the SDA pin number (if no i2c is provided)
          freq     -- I2C bus frequency (default: 400kHz)
          address  -- I2C address of the sensor (default: 0x40)
        """
        self.address = address
        if i2c is not None:
            self.i2c = i2c
        else:
            if scl_pin is None or sda_pin is None:
                raise ValueError("You must supply either an I2C instance or both scl_pin and sda_pin.")
            self.i2c = machine.I2C(1, scl=machine.Pin(scl_pin), sda=machine.Pin(sda_pin), freq=freq)

    def read(self):
        """
        Reads the sensor and returns the temperature (°F) and humidity (%RH).

        Returns:
          A tuple: (temperature_in_F, humidity)
        """
        # Request a combined measurement by writing register 0x00.
        # (The Arduino example writes 0x00 then reads 4 bytes.)
        try:
            self.i2c.writeto(self.address, b'\x00')
        except Exception as e:
            raise Exception("I2C write failed: " + str(e))
        
        # Delay to allow the sensor to perform the measurement (20 ms as in the Arduino code)
        time.sleep(0.03)
        
        # Read 4 bytes from the sensor.
        try:
            raw = self.i2c.readfrom(self.address, 4)
        except Exception as e:
            raise Exception("I2C read failed: " + str(e))
        
        if len(raw) != 4:
            raise Exception("Expected 4 bytes from sensor, but got {} bytes.".format(len(raw)))
        
        # Extract the temperature and humidity raw values.
        raw_temp = (raw[0] << 8) | raw[1]
        raw_hum  = (raw[2] << 8) | raw[3]
        
        # Convert raw values to human‐readable units.
        temp_c = (raw_temp * 165.0 / 65535.0) - 40.0
        humidity = (raw_hum * 100.0) / 65535.0
        temp_f = temp_c * 9.0/5.0 + 32.0

        return (temp_f, humidity)
    
    def temp(self):
        return round(self.read()[0],1)
    def humidity(self):
        return round(self.read()[1],1)
    


# =========================
# Example usage:
# =========================
# For MicroPython (e.g., on an ESP32 or similar board):
#
#   import machine
#   import time
#   from sen0546 import SEN0546  # assuming you save this code as sen0546.py
#
#   # Option 1: Create your own I2C instance and pass it to the sensor:
#   i2c = machine.I2C(0, scl=machine.Pin(17), sda=machine.Pin(16), freq=400000)
#   sensor = SEN0546(i2c=i2c)
#
#   # Option 2: Let the sensor class create the I2C object (provide pin numbers):
#   # sensor = SEN0546(scl_pin=17, sda_pin=16)
#
#   while True:
#       try:
#           temp_f, humidity = sensor.read()
#           print("Temperature: {:.2f} °F   Humidity: {:.2f}%".format(temp_f, humidity))
#       except Exception as err:
#           print("Sensor read error:", err)
#       time.sleep(1)

if __name__ == "__main__":
    sensor = SEN0546(scl_pin=19, sda_pin=18) 
    while True:
        try:
            print(f"Temperature: {sensor.temp()} °F   Humidity: {sensor.humidity()}%")
        except Exception as e:
            print("Sensor read error:", e)
        time.sleep(1)