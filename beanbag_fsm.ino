#include <mpu6050_esp32.h>
#include <WiFi.h>
#include<math.h>
#include<string.h>
#include <TFT_eSPI.h> // Graphics and font library for ST7735 driver chip
#include <SPI.h>
TFT_eSPI tft = TFT_eSPI();  // Invoke library, pins defined in User_Setup.h

uint8_t calibrate_state = 0; // calibration state variable
uint8_t state = 1; // recording state variable

const char USER[] = "nick";
const int game_id = 2;
const char POST_URL[] = "GET http://608dev-2.net/sandbox/sc/nldow/server_fsm.py?game_id=2 HTTP/1.1\r\n"; //CHANGE THIS TO YOUR TEAM'S URL
char network[] = "MIT";
char password[] = "";

const uint16_t IN_BUFFER_SIZE = 1000; //size of buffer to hold HTTP request
const uint16_t OUT_BUFFER_SIZE = 1000; //size of buffer to hold HTTP response
const int RESPONSE_TIMEOUT = 6000; //ms to wait for response from host
char request_buffer[IN_BUFFER_SIZE]; //char array buffer to hold HTTP request
char response_buffer[OUT_BUFFER_SIZE]; //char array buffer to hold HTTP response

float xy_acc_mag = 0;  //used for holding the magnitude of acceleration on xy plane
float z_acc_mag = 0; //used for holding the magnitude of acceleration on z axis

float z_vel = 0;
float xy_vel = 0;

int prev_sample;
int wait_state;

const float ZOOM = 9.81; //for display (converts readings into m/s^2)...used for visualizing only
const float STEP_THRESHOLD = 15.0;

const uint8_t LOOP_PERIOD = 10; //milliseconds
uint32_t primary_timer = 0;
float x, y, z; //variables for grabbing x,y,and z values
float angle;
float yz, xz, xy;
float xshift, yshift, zshift;

MPU6050 imu; //imu object called, appropriately, imu

const int RECORD_BUTTON = 45;

const int SAMPLE_FREQ = 25;

bool calibrated = false;

void setup() {
  Serial.begin(115200); //for debugging if needed.
  delay(50); //pause to make sure comms get set up
  Wire.begin();
  WiFi.begin(network, password);
  //if using channel/mac specification for crowded bands use the following:
  //WiFi.begin(network, password, channel, bssid);


  uint8_t count = 0; //count used for Wifi check times
  Serial.print("Attempting to connect to ");
  Serial.println(network);
  while (WiFi.status() != WL_CONNECTED && count < 12) {
    delay(500);
    Serial.print(".");
    count++;
  }
  delay(2000);
  if (WiFi.isConnected()) { //if we connected then print our IP, Mac, and SSID we're on
    Serial.println("CONNECTED!");
    Serial.println(WiFi.localIP().toString() + " (" + WiFi.macAddress() + ") (" + WiFi.SSID() + ")");
    delay(500);
  } else { //if we failed to connect just Try again.
    Serial.println("Failed to Connect :/  Going to restart");
    Serial.println(WiFi.status());
    ESP.restart(); // restart the ESP (proper way)
  }


  delay(50); //pause to make sure comms get set up
  if (imu.setupIMU(1)) {
    Serial.println("IMU Connected!");
  } else {
    Serial.println("IMU Not Connected :/");
    Serial.println("Restarting");
    ESP.restart(); // restart the ESP (proper way)
  }
  tft.init(); //initialize the screen
  tft.setRotation(2); //set rotation for our layout
  primary_timer = millis();
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);

  pinMode(RECORD_BUTTON, INPUT_PULLUP);
  prev_sample = millis();
  wait_state = 0;
}

void loop() {
  if (!calibrated) {
    calibrating_fsm();
  } else if (wait_state == 0){
    if (millis() - primary_timer > 4000){
      primary_timer = millis();
      poll_server();
      if (response_buffer[6] == '3') wait_state = 1;
    }
  } else {
    recording_fsm();
  }
  char output[60];
  sprintf(output, "%4.2f  \n%4.2f  \n%4.2f  ", x, y, z); //render numbers with %4.2 float formatting
  tft.setCursor(0, 0, 4);
  tft.println(output);
}

void calibrating_fsm() {
  if (calibrate_state == 0) {
    Serial.println("Calibration step 1: hold record for 3 seconds while holding beanbag still.");
    if(!digitalRead(RECORD_BUTTON)) {
      Serial.println("Calibration recording beginning");
      calibrate_state = 1;
    }
  } else if (calibrate_state == 1) {
    if (!digitalRead(RECORD_BUTTON) && millis() - prev_sample > SAMPLE_FREQ) {
      imu.readAccelData(imu.accelCount);
      infinite_avg(&x, ZOOM * imu.accelCount[0] * imu.aRes);
      infinite_avg(&y, ZOOM * imu.accelCount[1] * imu.aRes);
      infinite_avg(&z, ZOOM * imu.accelCount[2] * imu.aRes);
    } else if (digitalRead(RECORD_BUTTON)) {
      xshift = -1*x;
      yshift = -1*y;
      zshift = -1*z;

      calibrate_state = 2;
      Serial.println("Calibration step 1 complete");
      Serial.println("Calibration step 2: record a throw in the direction of the board.");
    }
  } else if (calibrate_state == 2) {
    calibrated = true;
  }
}

void recording_fsm() {
  if (state == 1) { // recording start
    xy_vel = 0;
    z_vel = 0;

    if (!digitalRead(RECORD_BUTTON)) {
      Serial.println("Recording beginning");
      state = 2;
    }
  } else if (state == 2) { // recording in progress
    if (!digitalRead(RECORD_BUTTON) && millis() - prev_sample > SAMPLE_FREQ) { // button is pressed and time has passed since last recording
      imu.readAccelData(imu.accelCount);
      imu.readGyroData(imu.gyroCount);
      x = ZOOM * imu.accelCount[0] * imu.aRes + xshift;
      y = ZOOM * imu.accelCount[1] * imu.aRes + yshift;
      z = ZOOM * imu.accelCount[2] * imu.aRes + zshift;
      //Serial.println(imu.gyroCount[0] * imu.gRes);

      xy_acc_mag = sqrt(x*x + y*y);
      z_acc_mag = z;

      xy_vel = xy_vel + (millis() - prev_sample)*xy_acc_mag/1000.0;
      z_vel = z_vel + (millis() - prev_sample)*z_acc_mag/1000.0;
      angle = tan(xy_vel/z_vel);
      prev_sample = millis();

    } else if (digitalRead(RECORD_BUTTON)) {
      Serial.println("Recorded Horizontal and Vertical Velocities: ");
      Serial.println(xy_vel);
      Serial.println(z_vel);

      post_throw(xy_vel, 0, z_vel);

      xy_vel = 0;
      z_vel = 0;

      state = 1;
      wait_state = 0;
    }
    Serial.print("Horizontal velocity:");
    Serial.print(xy_vel);
    Serial.print(",");
    Serial.print("Vertical velocity:");
    Serial.print(z_vel);
    Serial.print(",");
    Serial.print("Throw angle:");
    Serial.println(angle);
  } 

}

void poll_server(){
  sprintf(request_buffer, "GET http://608dev-2.net/sandbox/sc/nldow/server_fsm.py?game_id=%d HTTP/1.1\r\n", game_id);
  strcat(request_buffer, "Host: 608dev-2.net\r\n");
  strcat(request_buffer, "Content-Type: application/x-www-form-urlencoded\r\n\r\n");
  do_http_request("608dev-2.net", request_buffer, response_buffer, OUT_BUFFER_SIZE, RESPONSE_TIMEOUT, true);
}

void post_throw(float vx, float vy, float vz){
  char body[100]; //for body
  sprintf(body, "type=throw"); //generate body, posting temp, humidity to server
  int body_len = strlen(body); //calculate body length (for header reporting)
  sprintf(request_buffer, "POST http://608dev-2.net/sandbox/sc/nldow/server_fsm.py?game_id=%d&user=%s&vx=%4.2f&vy=%4.2f&vz=%4.2f HTTP/1.1\r\n", game_id, USER, vx, vy, vz);
  strcat(request_buffer, "Host: 608dev-2.net\r\n");
  strcat(request_buffer, "Content-Type: application/x-www-form-urlencoded\r\n");
  sprintf(request_buffer + strlen(request_buffer), "Content-Length: %d\r\n", body_len); //append string formatted to end of request buffer
  strcat(request_buffer, "\r\n"); //new line from header to body
  strcat(request_buffer, body); //body
  strcat(request_buffer, "\r\n"); //new line
  do_http_request("608dev-2.net", request_buffer, response_buffer, OUT_BUFFER_SIZE, RESPONSE_TIMEOUT, true);
}

void infinite_avg(float* average, float input){
    *average = 0.99*(*average) + 0.01*input;
}

/*----------------------------------
  char_append Function:
  Arguments:
     char* buff: pointer to character array which we will append a
     char c:
     uint16_t buff_size: size of buffer buff

  Return value:
     boolean: True if character appended, False if not appended (indicating buffer full)
*/
uint8_t char_append(char* buff, char c, uint16_t buff_size) {
  int len = strlen(buff);
  if (len > buff_size) return false;
  buff[len] = c;
  buff[len + 1] = '\0';
  return true;
}

/*----------------------------------
   do_http_request Function:
   Arguments:
      char* host: null-terminated char-array containing host to connect to
      char* request: null-terminated char-arry containing properly formatted HTTP request
      char* response: char-array used as output for function to contain response
      uint16_t response_size: size of response buffer (in bytes)
      uint16_t response_timeout: duration we'll wait (in ms) for a response from server
      uint8_t serial: used for printing debug information to terminal (true prints, false doesn't)
   Return value:
      void (none)
*/
void do_http_request(char* host, char* request, char* response, uint16_t response_size, uint16_t response_timeout, uint8_t serial) {
  WiFiClient client; //instantiate a client object
  if (client.connect(host, 80)) { //try to connect to host on port 80
    if (serial) Serial.print(request);//Can do one-line if statements in C without curly braces
    client.print(request);
    memset(response, 0, response_size); //Null out (0 is the value of the null terminator '\0') entire buffer
    uint32_t count = millis();
    while (client.connected()) { //while we remain connected read out data coming back
      client.readBytesUntil('\n', response, response_size);
      if (serial) Serial.println(response);
      if (strcmp(response, "\r") == 0) { //found a blank line!
        break;
      }
      memset(response, 0, response_size);
      if (millis() - count > response_timeout) break;
    }
    memset(response, 0, response_size);
    count = millis();
    while (client.available()) { //read out remaining text (body of response)
      char_append(response, client.read(), OUT_BUFFER_SIZE);
    }
    if (serial) Serial.println(response);
    client.stop();
    if (serial) Serial.println("-----------");
  } else {
    if (serial) Serial.println("connection failed :/");
    if (serial) Serial.println("wait 0.5 sec...");
    client.stop();
  }
}
