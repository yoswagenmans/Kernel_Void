#include <WiFi.h> //Connect to WiFi Network
#include <SPI.h>
#include <TFT_eSPI.h>
#include <mpu6050_esp32.h>
#include<math.h>
#include<string.h>

TFT_eSPI tft = TFT_eSPI();
MPU6050 imu;

int BUTTON_PIN = 38;
uint32_t timer;
int thrown;
int backwards;
int button_state = 1;
int pos;

int LOOP = 3;
void setup() {
  Serial.begin(115200);
  delay(50); //pause to make sure comms get set up
  Wire.begin();
  delay(50); //pause to make sure comms get set up
  tft.init();
  tft.setRotation(2);
  tft.setTextSize(1);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_GREEN, TFT_BLACK); //set color of font to green foreground, black background
  pinMode(BUTTON_PIN, INPUT_PULLUP);
}

void loop() {
  uint8_t button_val = digitalRead(BUTTON_PIN);
  if (millis() - timer >= LOOP && !thrown){
    tft.drawRect(44, 50, 40, 60, TFT_GREEN);
    tft.drawCircle(64, 60, 5, TFT_GREEN);
    if (!backwards) {
      pos += 1;
      if (pos == 128) {
        backwards = 1;
      }
      tft.drawFastVLine(pos-1, 0, 500, TFT_BLACK);
    }
    else {
      pos -= 1;
      if (pos == 0) {
        backwards = 0;
      }
      tft.drawFastVLine(pos+1, 0, 500, TFT_BLACK);
    }
    tft.drawFastVLine(pos, 0, 500, TFT_RED);
    timer = millis();
  }
  if (!button_val && button_state) {
    thrown = 1;
    if (pos < 44 | pos > 84) {
      Serial.println("Missed!");
    }
    else {
      Serial.println((pos-44)/40.0);
    }
  }
  button_state = button_val;

}
