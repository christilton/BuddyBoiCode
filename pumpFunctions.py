def control_pump(state):
    command = bytearray([0x01]) if state == 'on' else bytearray([0x00])
    trinket.writeto(TRINKET_ADDRESS, command)

async def manage_pump():
    while True:
        FEED_KEY = 'pump-gecko'
        url = f'https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/{FEED_KEY}/data'
        headers = {
        'X-AIO-Key': ADAFRUIT_AIO_KEY,
        'Content-Type': 'application/json'
        }
        response = requests.get(url+"/last",headers=headers)
        data = response.json()
        if int(data["value"]) == 1:
            control_pump('on')  # Turn the pump on
            print("Pump turned ON manually.")
            await asyncio.sleep(10)  # Run the pump for 30 seconds
            control_pump('off')  # Turn the pump off
            requests.post(url,headers=headers,json={"value":0})
        if current_hour == 8:  # Start pump at 8:00 AM
            control_pump('on')  # Turn the pump on
            print("Pump turned ON at 8:00 AM.")
            await asyncio.sleep(30)  # Run the pump for 30 seconds
            control_pump('off')  # Turn the pump off
            print("Pump turned OFF at 8:00 AM.")
        elif current_hour == 21:  # Start pump at 9:00 PM
            control_pump('on')  # Turn the pump on
            print("Pump turned ON at 9:00 PM.")
            await asyncio.sleep(30)  # Run the pump for 30 seconds
            control_pump('off')  # Turn the pump off
            print("Pump turned OFF at 9:00 PM.")
        await asyncio.sleep(120)  # Check every 2 minutes

async def button_checker():
    lights_on = False  # Variable to track lights state
    global current_hour
    while True:
        # Check if the button is pressed
        if button_pin.value() == 0:  # Button pressed (active low)
            if current_hour >= 21 or current_hour < 7:  # Nighttime
                if not lights_on:
                    # Turn the lights on red
                    send_color(255, 0, 0)  # Red color
                    print("Button pressed. Lights turned ON in red.")
                    lights_on = True
                else:
                    # Turn the lights off
                    send_color(0, 0, 0)  # Off color
                    print("Button pressed. Lights turned OFF.")
                    lights_on = False
                await asyncio.sleep(2)  # Delay to debounce the button
        await asyncio.sleep(0.1)  # Check button every 0.1 second