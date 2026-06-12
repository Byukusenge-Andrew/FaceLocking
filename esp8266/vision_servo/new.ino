#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Servo.h>

// --- Configuration ---
const char* ssid = "CM232_Airtel_4C62";
const char* password = "1234567890";


const char* mqtt_server = "157.173.101.159"; 
const int mqtt_port = 1883;
const char* client_id = "esp8266_andrew";
const char* topic_movement = "vision/andrew/movement";
const char* topic_heartbeat = "vision/andrew/heartbeat";

// Servo Configuration
const int servoPin = D4; 
float currentAngle = 90.0;   
Servo myServo;
bool isServoAttached = false;
unsigned long lastServoMoveTime = 0;
const unsigned long SERVO_DETACH_TIMEOUT = 1000; // 1 second of inactivity to detach
const int MIN_ANGLE = 15;   // Minimum servo angle (increase if servo stalls/delays at right end)
const int MAX_ANGLE = 165;  // Maximum servo angle (decrease if servo stalls/delays at left end)

void attachServo() {
  if (!isServoAttached) {
    myServo.attach(servoPin);
    isServoAttached = true;
    Serial.println("Servo attached.");
  }
}

void detachServo() {
  if (isServoAttached) {
    myServo.detach();
    isServoAttached = false;
    Serial.println("Servo detached to prevent jitter.");
  }
}

// --- Search Mode Variables ---
bool isSearching = true;         // Start in search mode by default
unsigned long lastSweepTime = 0;
const int SWEEP_INTERVAL = 100;  // Time between sweep steps in ms (increase to slow down sweep)
const int SWEEP_STEP = 1;        // Sweep step size in degrees
int sweepStep = SWEEP_STEP;      // Dynamic sweep step

// --- Tracking Mode Variables ---
const float TRACKING_STEP = 3.0;      // Tracking step size in degrees (decrease for smoother/slower tracking)
const float TRACKING_DIRECTION = 1.0; // Tracking direction multiplier (1 or -1). Change to -1 if camera tracks away from you.
const unsigned long TRACKING_COOLDOWN_MS = 120; // Minimum time between tracking adjustments in ms (prevents latency overshoot)

// --- Watchdog Timer Variables ---
unsigned long lastFaceDetectTime = 0;
const unsigned long FACE_TIMEOUT = 2000; // 2 seconds without a face triggers a search

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.println("\nInitializing WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.println("WiFi initialized. Connecting in background...");
}

void moveServo(float delta) {
  float oldAngle = currentAngle;
  currentAngle += delta;
  if (currentAngle < MIN_ANGLE) currentAngle = MIN_ANGLE;
  if (currentAngle > MAX_ANGLE) currentAngle = MAX_ANGLE;
  
  attachServo();
  int us = 544 + (int)((currentAngle / 180.0) * (2400 - 544)); // Precise float-to-us mapping
  myServo.writeMicroseconds(us);
  lastServoMoveTime = millis();
  
  Serial.print("Servo angle updated from ");
  Serial.print(oldAngle);
  Serial.print(" to ");
  Serial.println(currentAngle);
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("MQTT IN [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

  // Extract "status" value from simple JSON format {"status": "VALUE", ...}
  String status = "";
  int statusIndex = message.indexOf("\"status\"");
  if (statusIndex >= 0) {
    int colonIndex = message.indexOf(":", statusIndex);
    if (colonIndex >= 0) {
      int firstQuote = message.indexOf("\"", colonIndex);
      if (firstQuote >= 0) {
        int secondQuote = message.indexOf("\"", firstQuote + 1);
        if (secondQuote >= 0) {
          status = message.substring(firstQuote + 1, secondQuote);
        }
      }
    }
  }

  // Fallback to substring matching if status not found in JSON
  if (status == "") {
    if (message.indexOf("MOVE_LEFT") >= 0) status = "MOVE_LEFT";
    else if (message.indexOf("MOVE_RIGHT") >= 0) status = "MOVE_RIGHT";
    else if (message.indexOf("CENTERED") >= 0) status = "CENTERED";
    else if (message.indexOf("NO_FACE") >= 0) status = "NO_FACE";
  }

  Serial.print("Parsed status: ");
  Serial.println(status);
  
  // Parse the commands and update the Watchdog Timer
  if (status == "MOVE_LEFT") {
    isSearching = false; 
    lastFaceDetectTime = millis(); // Reset the timer!
    if (millis() - lastServoMoveTime >= TRACKING_COOLDOWN_MS) {
      moveServo(TRACKING_STEP * TRACKING_DIRECTION); // Turn left (e.g. increase angle)
    }
  } 
  else if (status == "MOVE_RIGHT") {
    isSearching = false; 
    lastFaceDetectTime = millis(); // Reset the timer!
    if (millis() - lastServoMoveTime >= TRACKING_COOLDOWN_MS) {
      moveServo(-TRACKING_STEP * TRACKING_DIRECTION); // Turn right (e.g. decrease angle)
    }
  } 
  else if (status == "CENTERED") {
    isSearching = false; 
    lastFaceDetectTime = millis(); // Reset the timer!
  } 
  else if (status == "NO_FACE") {
    // Let the watchdog timer handle starting the search after FACE_TIMEOUT (2s)
  }
}

unsigned long lastReconnectAttempt = 0;

bool reconnectNonBlocking() {
  Serial.print("Attempting MQTT connection...");
  String uniqueClientId = String(client_id) + "_" + String(ESP.getChipId());
  if (client.connect(uniqueClientId.c_str())) {
    Serial.println("Connected!");
    client.subscribe(topic_movement);
    return true;
  }
  Serial.print("failed, rc=");
  Serial.print(client.state());
  Serial.println(" trying again in 5s");
  return false;
}

void setup() {
  Serial.begin(115200);
  
  // Initialize Servo
  attachServo();
  int us = 544 + (int)((currentAngle / 180.0) * (2400 - 544));
  myServo.writeMicroseconds(us);
  lastServoMoveTime = millis();

  setup_wifi();
  espClient.setTimeout(500); // Set TCP connection timeout to 500ms (non-blocking safeguard)
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  unsigned long now = millis();

  // --- NON-BLOCKING WIFI & MQTT CONNECTION CHECK ---
  static bool wifiWasConnected = false;
  bool wifiIsConnected = (WiFi.status() == WL_CONNECTED);
  
  if (wifiIsConnected && !wifiWasConnected) {
    Serial.println("\nWiFi Connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    wifiWasConnected = true;
  } else if (!wifiIsConnected && wifiWasConnected) {
    Serial.println("\nWiFi Disconnected!");
    wifiWasConnected = false;
  }

  if (wifiIsConnected) {
    if (!client.connected()) {
      if (now - lastReconnectAttempt > 5000) {
        lastReconnectAttempt = now;
        reconnectNonBlocking();
      }
    } else {
      client.loop();
    }
  }

  // --- WATCHDOG TIMER ---
  // If we aren't currently searching, but it's been more than 2 seconds 
  // since we last saw a face, force the system back into search mode.
  if (!isSearching && (millis() - lastFaceDetectTime > FACE_TIMEOUT)) {
    Serial.println("Face lost! Watchdog triggered. Starting search...");
    isSearching = true;
    lastFaceDetectTime = millis(); // Safeguard to prevent immediate watchdog printing loop
  }

  // --- NON-BLOCKING SEARCH SWEEP ---
  if (isSearching) {
    if (now - lastSweepTime > SWEEP_INTERVAL) { 
      lastSweepTime = now;
      currentAngle += sweepStep;

      if (currentAngle >= MAX_ANGLE) {
        currentAngle = MAX_ANGLE;
        sweepStep = -SWEEP_STEP; 
      } else if (currentAngle <= MIN_ANGLE) {
        currentAngle = MIN_ANGLE;
        sweepStep = SWEEP_STEP;  
      }
      attachServo();
      int us = 544 + (int)((currentAngle / 180.0) * (2400 - 544));
      myServo.writeMicroseconds(us);
      lastServoMoveTime = millis();
    }
  }

  // --- AUTO-DETACH TO PREVENT JITTER ---
  if (isServoAttached && !isSearching && (now - lastServoMoveTime > SERVO_DETACH_TIMEOUT)) {
    detachServo();
  }

  // --- SYSTEM HEARTBEAT ---
  static unsigned long lastHeartbeat = 0;
  if (now - lastHeartbeat > 5000) {
    lastHeartbeat = now;
    String heartbeat = "{\"node\": \"esp8266\", \"status\": \"ONLINE\"}";
    client.publish(topic_heartbeat, heartbeat.c_str());
  }
}