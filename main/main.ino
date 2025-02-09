#include <Wire.h>
#include <Adafruit_NeoPixel.h>

#define PIN_NEOPIXEL 0
#define NUMPIXELS 60
#define PIN_PUMP 6
#define LED 13

Adafruit_NeoPixel pixels(NUMPIXELS, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

uint8_t currentR = 0, currentG = 0, currentB = 0, currentBrightness = 0;

void setup() {
  Wire.begin(0x12);  // Join I2C bus with address #0x12
  Wire.onReceive(receiveEvent);  // Register event
  pixels.begin();  // Initialize NeoPixel strip
  pinMode(PIN_PUMP, OUTPUT);  // Initialize pump pin
  pinMode(LED, OUTPUT);  // Initialize LED pin
}

void loop() {
  // Nothing to do here, all work is done in receiveEvent
}

void fadeToColor(uint8_t newR, uint8_t newG, uint8_t newB, uint8_t newBrightness) {
  int steps = 50; // Number of steps for fading
  for (int i = 0; i <= steps; i++) {
    uint8_t r = map(i, 0, steps, currentR, newR);
    uint8_t g = map(i, 0, steps, currentG, newG);
    uint8_t b = map(i, 0, steps, currentB, newB);
    uint8_t brightness = map(i, 0, steps, currentBrightness, newBrightness);
    
    pixels.setBrightness(brightness);
    for (int j = 0; j < NUMPIXELS; j++) {
      pixels.setPixelColor(j, pixels.Color(r, g, b));
    }
    pixels.show();
    delay(10); // Adjust speed of fading
  }
  
  currentR = newR;
  currentG = newG;
  currentB = newB;
  currentBrightness = newBrightness;
}

void receiveEvent(int howMany) {
  if (howMany == 5) {  // RGB color data
    uint8_t type = Wire.read();
    uint8_t r = Wire.read();
    uint8_t g = Wire.read();
    uint8_t b = Wire.read();
    uint8_t brightness = Wire.read();

    if (type == 1) {
      fadeToColor(r, g, b, brightness);
    }
    else {
      pixels.setPixelColor(type, pixels.Color(r, g, b));
      pixels.setBrightness(brightness);
      pixels.show();
    }
  }
}
