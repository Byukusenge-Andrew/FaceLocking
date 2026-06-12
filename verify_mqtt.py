# verify_mqtt.py
"""
Verify MQTT messages on the broker.
Subscribes to movement and heartbeat topics for both 'andrew' and 'team313'.

Run:
  python verify_mqtt.py
"""

import time
import json
import paho.mqtt.client as mqtt

BROKER = "157.173.101.159"
PORT = 1883

TOPICS = [
    "vision/andrew/movement",
    "vision/andrew/heartbeat",
    "vision/team313/movement",
    "vision/team313/heartbeat"
]

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected successfully to MQTT Broker: {BROKER}")
        for topic in TOPICS:
            client.subscribe(topic)
            print(f"Subscribed to topic: {topic}")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        # Pretty print if it's JSON
        try:
            data = json.loads(payload)
            # Remove face image from print to keep logs clean
            if "face_image" in data:
                data["face_image"] = "<base64_image_data>"
            payload_str = json.dumps(data)
        except json.JSONDecodeError:
            payload_str = payload
            
        print(f"[{time.strftime('%H:%M:%S')}] MQTT IN [{msg.topic}]: {payload_str}")
    except Exception as e:
        print(f"Error handling message: {e}")

def main():
    print(f"Connecting to MQTT Broker: {BROKER}:{PORT}...")
    client = mqtt.Client(client_id="verify_mqtt_listener")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(BROKER, PORT, 60)
        print("Starting event loop. Press Ctrl+C to exit.")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nExiting.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
