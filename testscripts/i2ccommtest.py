from machine import Pin, I2C
import utime

# Define I2C pins
SDA_PIN = 0  # Adjust pins as necessary
SCL_PIN = 1

# Initialize I2C bus
i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))

# Address of the Arduino Pro Trinket (Slave)
TRINKET_ADDRESS = 0x12  # Example address

# Function to send RGB color to the Trinket
def send_color(r, g, b):
    color_data = bytearray([r, g, b])
    i2c.writeto(TRINKET_ADDRESS, color_data)

# Example: Set NeoPixel color to red
send_color(255, 0, 0)

# Main loop (cycle through colors)
colors = [
    (255, 255, 0),   # Bright Yellow
    (255, 239, 70),  # Light Yellow
    (255, 223, 105), # Golden Yellow
    (255, 207, 140), # Soft Yellow
    (255, 191, 175),
    (0,0,180)# Pale Yellow
]

while True:
    for color in colors:
        send_color(*color)
        print(color)
        utime.sleep(1)  # Wait 1 second between colors
