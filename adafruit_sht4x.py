import time
import struct
from machine import I2C, Pin

_SHT4X_DEFAULT_ADDR = const(0x44)  # SHT4X I2C Address
_SHT4X_READSERIAL = const(0x89)  # Read Out of Serial Register
_SHT4X_SOFTRESET = const(0x94)  # Soft Reset

class CV:
    """struct helper"""

    @classmethod
    def add_values(cls, value_tuples):
        """Add CV values to the class"""
        cls.string = {}
        cls.delay = {}

        for value_tuple in value_tuples:
            name, value, string, delay = value_tuple
            setattr(cls, name, value)
            cls.string[value] = string
            cls.delay[value] = delay

    @classmethod
    def is_valid(cls, value):
        """Validate that a given value is a member"""
        return value in cls.string

class Mode(CV):
    """Options for ``power_mode``"""
    NOHEAT_HIGHPRECISION = 0xFD

Mode.add_values(
    (
        ("NOHEAT_HIGHPRECISION", 0xFD, "No heater, high precision", 0.01),
        ("NOHEAT_MEDPRECISION", 0xF6, "No heater, med precision", 0.005),
        ("NOHEAT_LOWPRECISION", 0xE0, "No heater, low precision", 0.002),
        ("HIGHHEAT_1S", 0x39, "High heat, 1 second", 1.1),
        ("HIGHHEAT_100MS", 0x32, "High heat, 0.1 second", 0.11),
        ("MEDHEAT_1S", 0x2F, "Med heat, 1 second", 1.1),
        ("MEDHEAT_100MS", 0x24, "Med heat, 0.1 second", 0.11),
        ("LOWHEAT_1S", 0x1E, "Low heat, 1 second", 1.1),
        ("LOWHEAT_100MS", 0x15, "Low heat, 0.1 second", 0.11),
    )
)

# Ensure the attributes are accessible


class SHT4x:
    """
    A driver for the SHT4x temperature and humidity sensor.

    :param int sda_pin: The pin the SDA line is connected to.
    :param int scl_pin: The pin the SCL line is connected to.
    :param int address: The I2C device address. Default is :const:`0x44`
    """

    def __init__(self, bus, sda_pin, scl_pin, address=_SHT4X_DEFAULT_ADDR):
        try:
            self.i2c = I2C(bus, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=100000)
        except OSError:
            raise ValueError("I2C bus or pins are invalid")
        self._buffer = bytearray(6)
        self.reset()
        self._mode = Mode.NOHEAT_HIGHPRECISION

    def serial_number(self):
        """The unique 32-bit serial number"""
        self._buffer[0] = _SHT4X_READSERIAL
        self.i2c.writeto(_SHT4X_DEFAULT_ADDR, self._buffer)
        time.sleep_ms(10)
        self.i2c.readfrom_into(_SHT4X_DEFAULT_ADDR, self._buffer)

        ser1 = self._buffer[0:2]
        ser1_crc = self._buffer[2]
        ser2 = self._buffer[3:5]
        ser2_crc = self._buffer[5]

        # check CRC of bytes
        if ser1_crc != self._crc8(ser1) or ser2_crc != self._crc8(ser2):
            raise RuntimeError("Invalid CRC calculated")

        serial = (ser1[0] << 24) + (ser1[1] << 16) + (ser2[0] << 8) + ser2[1]
        return serial

    def reset(self):
        """Perform a soft reset of the sensor, resetting all settings to their power-on defaults"""
        self._buffer[0] = _SHT4X_SOFTRESET
        self.i2c.writeto(_SHT4X_DEFAULT_ADDR, self._buffer)
        time.sleep_ms(1)

    @property
    def mode(self):
        """The current sensor reading mode (heater and precision)"""
        return self._mode

    @mode.setter
    def mode(self, new_mode):
        if not Mode.is_valid(new_mode):
            raise AttributeError("mode must be a Mode")
        self._mode = new_mode

    @property
    def relative_humidity(self):
        """The current relative humidity in % rH. This is a value from 0-100%."""
        return self.measurements()[1]

    @property
    def temperature(self):
        """The current temperature in degrees Celsius"""
        return self.measurements()[0]



    def measurements(self):
        """both `temperature` and `relative_humidity`, read simultaneously"""

        temperature = None
        humidity = None
        command = self._mode

        self._buffer[0] = command
        self.i2c.writeto(_SHT4X_DEFAULT_ADDR, self._buffer)
        time.sleep_ms(int(Mode.delay[self._mode] * 1000))  # Delay in milliseconds
        self.i2c.readfrom_into(_SHT4X_DEFAULT_ADDR, self._buffer)

        try:
            # separate the read data
            temp_data = self._buffer[0:2]
            temp_crc = self._buffer[2]
            humidity_data = self._buffer[3:5]
            humidity_crc = self._buffer[5]

            # check CRC of bytes
            if temp_crc != self._crc8(temp_data) or humidity_crc != self._crc8(
                humidity_data
            ):
                raise RuntimeError("Invalid CRC calculated")

            # decode data into human values:
            # convert bytes into 16-bit unsigned integer
            temperature = struct.unpack(">H", temp_data)[0]
            humidity = struct.unpack(">H", humidity_data)[0]

            # Calculate temperature and humidity
            temperature = -47.5 + 175.0 * temperature / 65535.0
            temperature = temperature*9/5+32
            humidity = -6.0 + 125.0 * humidity / 65535.0
            humidity = max(min(humidity, 100), 0)

        except OSError as e:
            if e.args[0] == 5:  # EIO 5 - I/O error
                print("EIO 5: I/O error occurred! Retrying...")
                self.reset()  # Optionally reset the sensor or try other recovery steps
                # Reset I2C communication


            else:
                raise  # Raise other exceptions as is

        return (temperature, humidity)

    ## CRC-8 formula from page 14 of SHTC3 datasheet
    # https://media.digikey.com/pdf/Data%20Sheets/Sensirion%20PDFs/HT_DS_SHTC3_D1.pdf
    # Test data [0xBE, 0xEF] should yield 0x92



    @staticmethod
    def _crc8(buffer):
        """verify the crc8 checksum"""
        crc = 0xFF
        for byte in buffer:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
        return crc & 0xFF  # return the bottom 8 bits

