#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Servo.h>

// --- Configuration ---
// WiFi Credentials
const char* ssid = "Main Hall";
const char* password = "Meeting@2024";

// MQTT Broker Setup
const char* mqtt_server = "157.173.101.159"; 
const int mqtt_port = 1883;
const char* client_id = "esp8266_team313";
const char* topic_movement = "vision/team313/movement";
const char* topic_heartbeat = "vision/team313/heartbeat";

// Servo Configuration
Servo myServo;
const int servoPin = D5; // GPIO14 on NodeMCU
int currentAngle = 90;   // Start at center (0-180 range)

// --- Search Mode Variables ---
bool isSearching = false;
unsigned long lastSweepTime = 0;
int sweepStep = 2;       // Degrees to move per "tick" during a search

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

// Helper function to move the servo during active tracking
void moveServo(int delta) {
  currentAngle += delta;
  
  // Constrain the angle to physical servo limits
  if (currentAngle < 0) currentAngle = 0;
  if (currentAngle > 180) currentAngle = 180;
  
  myServo.write(currentAngle);
  Serial.print("Tracking - Angle: ");
  Serial.println(currentAngle);
}

// Triggers when a new MQTT message arrives
void callback(char* topic, byte* payload, unsigned int length) {
  // Convert incoming payload to a String
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("Received Command: ");
  Serial.println(message);

  // Parse the commands (using >= 0 because the index starts at 0)
  if (message.indexOf("MOVE_LEFT") >= 0) {
    isSearching = false; // Face found, stop sweeping!
    moveServo(-3);       // Adjust the -3 to make it turn faster/slower
  } 
  else if (message.indexOf("MOVE_RIGHT") >= 0) {
    isSearching = false; // Face found, stop sweeping!
    moveServo(3);        // Adjust the 3 to make it turn faster/slower
  } 
  else if (message.indexOf("CENTERED") >= 0) {
    isSearching = false; // Face found, stop sweeping!
    // Servo stays put when the face is in the deadzone
  } 
  else if (message.indexOf("NO_FACE") >= 0) {
    isSearching = true;  // Face lost, trigger the autonomous search loop
  }
}

// Reconnects to MQTT if the connection drops
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    
    if (client.connect(client_id)) {
      Serial.println("Connected to Broker!");
      client.subscribe(topic_movement); // Re-subscribe to the topic
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  
  // Initialize Servo
  myServo.attach(servoPin);
  myServo.write(currentAngle); // Point forward on boot

  // Initialize Network & MQTT
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  // Ensure we stay connected to the MQTT broker
  if (!client.connected()) {
    reconnect();
  }
  client.loop(); // Process incoming messages

  unsigned long now = millis();

  // --- NON-BLOCKING SEARCH MODE (Radar Sweep) ---
  if (isSearching) {
    // Move the servo 2 degrees every 30 milliseconds
    if (now - lastSweepTime > 30) { 
      lastSweepTime = now;
      currentAngle += sweepStep;

      // Reverse direction if it hits the mechanical boundaries (0 or 180)
      if (currentAngle >= 180) {
        currentAngle = 180;
        sweepStep = -2; // Switch to sweeping left
      } else if (currentAngle <= 0) {
        currentAngle = 0;
        sweepStep = 2;  // Switch to sweeping right
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