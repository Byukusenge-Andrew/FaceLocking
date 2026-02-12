"""
vision_node.py
Simulated Vision Node for Distributed Vision-Control System.
Tracks face and publishes movement commands via MQTT.
Topic: vision/team313/movement
"""

import time
import argparse
import cv2
import json
import numpy as np
import paho.mqtt.client as mqtt
from pathlib import Path

# Add src to path if needed to import modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.haar_5pt import Haar5ptDetector

# Configuration
DEFAULT_BROKER = "localhost" 
PORT = 1883
TEAM_ID = "team313"
TOPIC_MOVEMENT = f"vision/{TEAM_ID}/movement"
TOPIC_HEARTBEAT = f"vision/{TEAM_ID}/heartbeat"

class VisionNode:
    def __init__(self, broker, port):
        self.client = mqtt.Client(client_id=f"{TEAM_ID}_vision_node")
        self.client.on_connect = self.on_connect
        self.client.connect(broker, port, 60)
        self.client.loop_start()
        
        self.det = Haar5ptDetector(min_size=(70, 70))
        self.running = True
        self.last_heartbeat = 0
        self.last_publish_time = 0

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected to MQTT Broker with result code {rc}")
        self.publish_heartbeat()

    def publish_movement(self, status, confidence=1.0):
        payload = {
            "status": status,
            "confidence": confidence,
            "timestamp": time.time()
        }
        self.client.publish(TOPIC_MOVEMENT, json.dumps(payload))
        print(f"Published: {payload}")

    def publish_heartbeat(self):
        payload = {
            "node": "pc",
            "status": "ONLINE",
            "timestamp": time.time()
        }
        self.client.publish(TOPIC_HEARTBEAT, json.dumps(payload))

    def run(self):
        cap = cv2.VideoCapture(0) # Use default camera (usually 0)
        if not cap.isOpened():
             cap = cv2.VideoCapture(1) # Try 1 if 0 fails
        
        print(f"Vision Node Started. Publishing to {TOPIC_MOVEMENT}")
        
        while self.running:
            ret, frame = cap.read()
            if not ret: break
            
            # Flip for mirror effect
            frame = cv2.flip(frame, 1)
            H, W = frame.shape[:2]
            
            # Detect Face
            faces = self.det.detect(frame)
            
            status = "NO_FACE"
            
            if faces:
                # Get largest face
                f = max(faces, key=lambda x: (x.x2-x.x1)*(x.y2-x.y1))
                
                # Draw Box
                cv2.rectangle(frame, (f.x1, f.y1), (f.x2, f.y2), (0, 255, 0), 2)
                
                # Calculate Center
                cx = (f.x1 + f.x2) / 2.0
                cx_norm = cx / W
                
                # Logic:
                # If face is on LEFT (cx_norm < 0.4), camera must move LEFT to center it.
                # If face is on RIGHT (cx_norm > 0.6), camera must move RIGHT to center it.
                
                if cx_norm < 0.4:
                    status = "MOVE_LEFT"
                elif cx_norm > 0.6:
                    status = "MOVE_RIGHT"
                else:
                    status = "CENTERED"
                
                cv2.putText(frame, f"{status} ({cx_norm:.2f})", (f.x1, f.y1-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            else:
                cv2.putText(frame, "NO FACE", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            
            # --- RATE LIMITING (10Hz) ---
            current_time = time.time()
            if current_time - self.last_publish_time >= 0.1:
                self.publish_movement(status)
                self.last_publish_time = current_time
            
            # Heartbeat every 5s
            if time.time() - self.last_heartbeat > 5:
                self.publish_heartbeat()
                self.last_heartbeat = time.time()
            
            cv2.imshow("Vision Node", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        self.client.loop_stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", type=str, default=DEFAULT_BROKER, help="MQTT Broker Address")
    args = parser.parse_args()

    node = VisionNode(args.broker, PORT)
    node.run()
