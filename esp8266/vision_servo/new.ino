#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Servo.h>

// --- Configuration ---
const char* ssid = "Main Hall";
const char* password = "Meeting@2024";

const char* mqtt_server = "157.173.101.159"; 
const int mqtt_port = 1883;
const char* client_id = "esp8266_team313";
const char* topic_movement = "vision/team313/movement";
const char* topic_heartbeat = "vision/team313/heartbeat";

// Servo Configuration
Servo myServo;
const int servoPin = D5; 
int currentAngle = 90;   

// --- Search Mode Variables ---
bool isSearching = true;         // Start in search mode by default
unsigned long lastSweepTime = 0;
int sweepStep = 2;       

// --- Watchdog Timer Variables ---
unsigned long lastFaceDetectTime = 0;
const unsigned long FACE_TIMEOUT = 2000; // 2 seconds without a face triggers a search

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.println("\nConnecting to WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
}

void moveServo(int delta) {
  currentAngle += delta;
  if (currentAngle < 0) currentAngle = 0;
  if (currentAngle > 180) currentAngle = 180;
  myServo.write(currentAngle);
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  // Parse the commands and update the Watchdog Timer
  if (message.indexOf("MOVE_LEFT") >= 0) {
    isSearching = false; 
    lastFaceDetectTime = millis(); // Reset the timer!
    moveServo(-3);       
  } 
  else if (message.indexOf("MOVE_RIGHT") >= 0) {
    isSearching = false; 
    lastFaceDetectTime = millis(); // Reset the timer!
    moveServo(3);        
  } 
  else if (message.indexOf("CENTERED") >= 0) {
    isSearching = false; 
    lastFaceDetectTime = millis(); // Reset the timer!
  } 
  else if (message.indexOf("NO_FACE") >= 0) {
    isSearching = true;  // Explicit command to start searching
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect(client_id)) {
      Serial.println("Connected!");
      client.subscribe(topic_movement); 
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" trying again in 5s");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  myServo.attach(servoPin);
  myServo.write(currentAngle); 

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long now = millis();

  // --- WATCHDOG TIMER ---
  // If we aren't currently searching, but it's been more than 2 seconds 
  // since we last saw a face, force the system back into search mode.
  if (!isSearching && (now - lastFaceDetectTime > FACE_TIMEOUT)) {
    Serial.println("Face lost! Watchdog triggered. Starting search...");
    isSearching = true;
  }

  // --- NON-BLOCKING SEARCH SWEEP ---
  if (isSearching) {
    if (now - lastSweepTime > 30) { 
      lastSweepTime = now;
      currentAngle += sweepStep;

      if (currentAngle >= 180) {
        currentAngle = 180;
        sweepStep = -2; 
      } else if (currentAngle <= 0) {
        currentAngle = 0;
        sweepStep = 2;  
      }
      myServo.write(currentAngle);
    }
  }

  // --- SYSTEM HEARTBEAT ---
  static unsigned long lastHeartbeat = 0;
  if (now - lastHeartbeat > 5000) {
    lastHeartbeat = now;
    String heartbeat = "{\"node\": \"esp8266\", \"status\": \"ONLINE\"}";
    client.publish(topic_heartbeat, heartbeat.c_str());
  }
}