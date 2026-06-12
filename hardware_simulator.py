# hardware_simulator.py
"""
Interactive GUI Hardware Simulator (Mock ESP8266 & SG90 Servo)
Mimics the exact state machine, MQTT subscriptions, watchdog, and sweep of the physical hardware.
Displays a real-time 2D graphical visualization of the tracking system.

Usage:
  python hardware_simulator.py --broker 157.173.101.159
"""

import time
import json
import argparse
import sys
import math
import threading
from queue import Queue
import tkinter as tk
from tkinter import ttk, messagebox
import paho.mqtt.client as mqtt

# --- Configuration ---
TEAM_ID = "andrew"
TOPIC_MOVEMENT = f"vision/{TEAM_ID}/movement"
TOPIC_HEARTBEAT = f"vision/{TEAM_ID}/heartbeat"
FACE_TIMEOUT = 2.0  # 2 seconds without a face triggers search mode (watchdog)
SWEEP_INTERVAL = 100  # 100ms sweep step in search mode (in ms)
SWEEP_STEP = 1
TRACKING_STEP = 3.0
TRACKING_DIRECTION = 1

class HardwareSimulatorGUI:
    def __init__(self, root, broker, port):
        self.root = root
        self.broker = broker
        self.port = port
        self.client_id = f"esp8266_{TEAM_ID}_simulated"
        
        # Simulated Hardware State
        self.current_angle = 90.0
        self.is_searching = True
        self.sweep_step = SWEEP_STEP
        self.last_face_detect_time = time.time()
        self.last_heartbeat_time = time.time()
        self.heartbeat_count = 0
        self.is_connected = False
        
        # Dual-speed Search Recovery variables
        self.fast_sweep_interval = 0.030 # 30ms in seconds
        self.slow_sweep_interval = 0.150 # 150ms in seconds
        self.sweep_interval = self.fast_sweep_interval
        self.last_sweep_time = 0.0
        self.last_known_face_angle = 90.0
        self.is_local_searching = False
        self.local_search_start_time = 0.0
        self.local_search_timeout = 5.0 # 5 seconds
        self.local_search_range = 20.0 # +/- 20 degrees
        
        # Interactive Target Face (initial position)
        self.face_x = 175
        self.face_y = 60
        self.dragging_face = False
        self.offline_mode = False  # If True, tracks the mouse-draggable face locally
        
        # Queue for thread-safe logging
        self.log_queue = Queue()
        
        # Configure Window
        self.root.title("ESP8266 & SG90 Servo Hardware Simulator")
        self.root.geometry("820x520")
        self.root.resizable(False, False)
        
        # Modern Styling
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Colors
        self.bg_dark = "#1c1c1e"
        self.bg_panel = "#2c2c2e"
        self.fg_white = "#ffffff"
        self.accent_blue = "#0a84ff"
        self.accent_green = "#30d158"
        self.accent_amber = "#ffd60a"
        self.accent_red = "#ff453a"
        
        self.root.configure(bg=self.bg_dark)
        
        # Build layout
        self.create_widgets()
        
        # Start MQTT
        self.start_mqtt()
        
        # Bind mouse events on Canvas for dragging the face
        self.canvas.bind("<ButtonPress-1>", self.on_face_press)
        self.canvas.bind("<B1-Motion>", self.on_face_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_face_release)
        
        # Start high-frequency update loops (using Tkinter's thread-safe clock)
        self.update_simulation()
        self.process_logs()

    def create_widgets(self):
        # Master Grid Configuration
        self.root.columnconfigure(0, weight=1) # Controls panel
        self.root.columnconfigure(1, weight=1) # Visualizer canvas
        self.root.rowconfigure(0, weight=1)
        
        # --- LEFT PANEL: CONTROL & METRICS ---
        left_panel = tk.Frame(self.root, bg=self.bg_dark, padx=15, pady=15)
        left_panel.grid(row=0, column=0, sticky="nsew")
        
        # Title
        title_label = tk.Label(left_panel, text="ESP8266 & SERVO MOCK", font=("Plus Jakarta Sans", 14, "bold"), fg=self.fg_white, bg=self.bg_dark)
        title_label.pack(anchor="w", pady=(0, 10))
        
        # Connection Stats Box
        stats_frame = tk.LabelFrame(left_panel, text=" Telemetry & Connection ", fg=self.fg_white, bg=self.bg_panel, bd=1, font=("Plus Jakarta Sans", 9, "bold"), padx=10, pady=10)
        stats_frame.pack(fill="x", pady=5)
        
        self.broker_label = tk.Label(stats_frame, text=f"Broker: {self.broker}:{self.port}", fg="#a1a1aa", bg=self.bg_panel, font=("Consolas", 9))
        self.broker_label.pack(anchor="w")
        
        self.conn_label = tk.Label(stats_frame, text="MQTT Status: Disconnected", fg=self.accent_red, bg=self.bg_panel, font=("Plus Jakarta Sans", 10, "bold"))
        self.conn_label.pack(anchor="w", pady=2)
        
        self.mode_label = tk.Label(stats_frame, text="System Mode: SEARCHING", fg=self.accent_amber, bg=self.bg_panel, font=("Plus Jakarta Sans", 10, "bold"))
        self.mode_label.pack(anchor="w", pady=2)
        
        self.angle_label = tk.Label(stats_frame, text="Servo Angle: 90°", fg=self.fg_white, bg=self.bg_panel, font=("Plus Jakarta Sans", 10, "bold"))
        self.angle_label.pack(anchor="w", pady=2)
        
        self.wd_label = tk.Label(stats_frame, text="Face Watchdog: Active", fg="#cbd5e1", bg=self.bg_panel, font=("Plus Jakarta Sans", 9))
        self.wd_label.pack(anchor="w", pady=2)

        self.hb_label = tk.Label(stats_frame, text="Heartbeats Sent: 0", fg="#cbd5e1", bg=self.bg_panel, font=("Plus Jakarta Sans", 9))
        self.hb_label.pack(anchor="w", pady=2)
        
        self.command_label = tk.Label(stats_frame, text="Motor Cmd: NONE", fg="#cbd5e1", bg=self.bg_panel, font=("Plus Jakarta Sans", 10, "bold"))
        self.command_label.pack(anchor="w", pady=2)
        self.last_cmd = "NONE"
        
        # Modes/Controls box
        control_frame = tk.LabelFrame(left_panel, text=" Test Controllers ", fg=self.fg_white, bg=self.bg_panel, bd=1, font=("Plus Jakarta Sans", 9, "bold"), padx=10, pady=10)
        control_frame.pack(fill="x", pady=10)
        
        # Offline Track checkbox
        self.offline_var = tk.BooleanVar(value=False)
        self.offline_cb = tk.Checkbutton(
            control_frame, 
            text="Enable Offline Face Tracking (Drag Face)", 
            variable=self.offline_var,
            onvalue=True, offvalue=False,
            command=self.toggle_offline_mode,
            bg=self.bg_panel, fg=self.fg_white,
            selectcolor=self.bg_dark,
            activebackground=self.bg_panel, activeforeground=self.fg_white,
            font=("Plus Jakarta Sans", 9)
        )
        self.offline_cb.pack(anchor="w", pady=5)
        
        # Log Box
        log_label = tk.Label(left_panel, text="System Logs:", font=("Plus Jakarta Sans", 10, "bold"), fg=self.fg_white, bg=self.bg_dark)
        log_label.pack(anchor="w", pady=(10, 2))
        
        log_frame = tk.Frame(left_panel)
        log_frame.pack(fill="both", expand=True)
        
        self.log_txt = tk.Text(log_frame, bg="#121214", fg="#34d399", font=("Consolas", 8), wrap="word", height=8, bd=0)
        self.log_txt.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_txt.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_txt.config(yscrollcommand=scrollbar.set)
        
        # --- RIGHT PANEL: VISUALIZER ---
        right_panel = tk.Frame(self.root, bg=self.bg_dark, padx=15, pady=15)
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        vis_label = tk.Label(right_panel, text="2D HARDWARE TRACKING VISUALIZATION", font=("Plus Jakarta Sans", 10, "bold"), fg=self.fg_white, bg=self.bg_dark)
        vis_label.pack(anchor="w", pady=(0, 10))
        
        # Canvas representation of Servo
        self.canvas_width = 360
        self.canvas_height = 360
        self.canvas = tk.Canvas(right_panel, width=self.canvas_width, height=self.canvas_height, bg="#121214", bd=0, highlightthickness=1, highlightbackground="#3a3a3c")
        self.canvas.pack(fill="both", expand=True)
        
        # Legend instructions
        legend_label = tk.Label(
            right_panel, 
            text="💡 Drag the yellow face with your mouse. Check the checkbox\nto simulate hardware tracking locally without a running vision script.", 
            font=("Plus Jakarta Sans", 8), fg="#a1a1aa", bg=self.bg_dark, justify="left"
        )
        legend_label.pack(anchor="w", pady=(10, 0))

    def log(self, text):
        self.log_queue.put(text)

    def process_logs(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_txt.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
            self.log_txt.see(tk.END)
        self.root.after(100, self.process_logs)

    def toggle_offline_mode(self):
        self.offline_mode = self.offline_var.get()
        if self.offline_mode:
            self.log("Offline Manual Test Mode: ENABLED. Subscriptions ignored.")
            self.is_searching = False
        else:
            self.log("Offline Manual Test Mode: DISABLED. Listening to Broker.")
            self.is_searching = True

    # --- CANVAS MOUSE BINDINGS (Draggable Target Face) ---
    def on_face_press(self, event):
        # Check if user clicked near the face coordinates (radius ~15 pixels)
        dist = math.hypot(event.x - self.face_x, event.y - self.face_y)
        if dist <= 20:
            self.dragging_face = True

    def on_face_drag(self, event):
        if self.dragging_face:
            # Constrain target face movements to the top half of the canvas
            self.face_x = max(20, min(self.canvas_width - 20, event.x))
            self.face_y = max(20, min(180, event.y)) # Keep it above the servo mount line
            self.draw_scene()

    def on_face_release(self, event):
        self.dragging_face = False

    # --- MQTT SUBSCRIPTION & CALLBACKS ---
    def start_mqtt(self):
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        
        self.log("Connecting to MQTT broker...")
        # Run MQTT client in background thread
        threading.Thread(target=self._mqtt_thread, daemon=True).start()

    def _mqtt_thread(self):
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_forever()
        except Exception as e:
            self.log(f"MQTT connection error: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            self.conn_label.config(text="MQTT Status: Connected", fg=self.accent_green)
            self.log("Connected to broker successfully!")
            client.subscribe(TOPIC_MOVEMENT)
            self.log(f"Subscribed to movement: {TOPIC_MOVEMENT}")
        else:
            self.is_connected = False
            self.conn_label.config(text=f"MQTT Status: Failed (rc {rc})", fg=self.accent_red)
            self.log(f"MQTT connection failed with code {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        self.conn_label.config(text="MQTT Status: Disconnected", fg=self.accent_red)
        self.log("Disconnected from broker.")

    def on_message(self, client, userdata, msg):
        if self.offline_mode:
            return # Ignore broker messages during offline mouse-interactive testing
            
        payload_str = msg.payload.decode('utf-8')
        self.log(f"MQTT IN: {payload_str}")
        
        # Parse commands (replicates search watchdog structure in C++ new.ino)
        cmd = "NONE"
        if "MOVE_LEFT" in payload_str or "MOVE_RIGHT" in payload_str or "CENTERED" in payload_str:
            self.is_searching = False
            self.is_local_searching = False
            self.last_face_detect_time = time.time()
            self.last_known_face_angle = self.current_angle
            
            if "MOVE_LEFT" in payload_str:
                cmd = "MOVE_LEFT"
                self.move_servo(TRACKING_STEP * TRACKING_DIRECTION)
            elif "MOVE_RIGHT" in payload_str:
                cmd = "MOVE_RIGHT"
                self.move_servo(-TRACKING_STEP * TRACKING_DIRECTION)
            elif "CENTERED" in payload_str:
                cmd = "CENTERED"
        elif "TRACK" in payload_str:
            self.is_searching = False
            self.is_local_searching = False
            self.last_face_detect_time = time.time()
            self.last_known_face_angle = self.current_angle
            cmd = "TRACK"
            
            # Extract delta from JSON
            delta = 0
            try:
                data = json.loads(payload_str)
                delta = data.get("delta", 0)
            except Exception:
                if "delta" in payload_str:
                    import re
                    parts = payload_str.split("delta")
                    match = re.search(r':\s*([-\d]+)', parts[1])
                    if match:
                        delta = int(match.group(1))
            
            # Clamp step to MAX_TRACKING_STEP = 8
            clamped_delta = max(-8, min(8, delta))
            self.move_servo(clamped_delta * TRACKING_DIRECTION)
        elif "NO_FACE" in payload_str:
            cmd = "NO_FACE"
            # Let the watchdog handle starting the search after timeout
            
        self.last_cmd = cmd

    def move_servo(self, delta):
        self.current_angle += delta
        if self.current_angle < 15:
            self.current_angle = 15
        elif self.current_angle > 165:
            self.current_angle = 165

    # --- SIMULATION STATE MACHINE TICKER ---
    def update_simulation(self):
        now = time.time()
             # 1. Check Offline manual tracking calculation
        if self.offline_mode:
            # Calculate angle between simulated servo center (180, 240) and target face
            dx = self.face_x - 180
            dy = 240 - self.face_y # Y goes downwards
            
            target_angle_rad = math.atan2(dy, dx)
            target_angle_deg = math.degrees(target_angle_rad)
            
            # Bound and steer servo towards the target face position
            if target_angle_deg < 15:
                target_angle_deg = 15
            elif target_angle_deg > 165:
                target_angle_deg = 165
                
            # Simulate smooth movement tracking step
            if abs(self.current_angle - target_angle_deg) > 2:
                if self.current_angle < target_angle_deg:
                    self.move_servo(TRACKING_STEP)
                    self.last_cmd = "MOVE_LEFT" if TRACKING_DIRECTION == 1 else "MOVE_RIGHT"
                else:
                    self.move_servo(-TRACKING_STEP)
                    self.last_cmd = "MOVE_RIGHT" if TRACKING_DIRECTION == 1 else "MOVE_LEFT"
            else:
                self.last_cmd = "CENTERED"
        else:
            # 2. Watchdog: Revert to auto searching if face is lost for > 2 seconds
            if not self.is_searching and (now - self.last_face_detect_time > FACE_TIMEOUT):
                self.is_searching = True
                self.is_local_searching = True
                self.local_search_start_time = now
                self.last_face_detect_time = now # Safeguard to prevent immediate watchdog printing loop
                self.sweep_interval = self.slow_sweep_interval
                self.last_cmd = "NO_FACE"
                self.log("Face lost! Watchdog triggered. Starting slow local recovery search...")
            
            # 3. Auto Searching sweep sweep step
            if self.is_searching:
                # If local searching, check timeout
                if self.is_local_searching and (now - self.local_search_start_time > self.local_search_timeout):
                    self.is_local_searching = False
                    self.sweep_interval = self.fast_sweep_interval
                    self.log("Local search timeout! Resuming fast full-range sweep...")
                
                # Check sweep tick
                if now - self.last_sweep_time >= self.sweep_interval:
                    self.last_sweep_time = now
                    self.current_angle += self.sweep_step
                    
                    if self.is_local_searching:
                        # Sweep within last_known_face_angle +/- LOCAL_SEARCH_RANGE
                        min_local = self.last_known_face_angle - self.local_search_range
                        max_local = self.last_known_face_angle + self.local_search_range
                        if min_local < 15: min_local = 15
                        if max_local > 165: max_local = 165
                        
                        if self.current_angle >= max_local:
                            self.current_angle = max_local
                            self.sweep_step = -SWEEP_STEP
                        elif self.current_angle <= min_local:
                            self.current_angle = min_local
                            self.sweep_step = SWEEP_STEP
                    else:
                        # Full-range sweep
                        if self.current_angle >= 165:
                            self.current_angle = 165
                            self.sweep_step = -SWEEP_STEP
                        elif self.current_angle <= 15:
                            self.current_angle = 15
                            self.sweep_step = SWEEP_STEP

        # 4. Periodic simulated device MQTT Heartbeats (every 5 seconds)
        if now - self.last_heartbeat_time >= 5.0:
            self.last_heartbeat_time = now
            self.heartbeat_count += 1
            self.hb_label.config(text=f"Heartbeats Sent: {self.heartbeat_count}")
            
            if self.is_connected and not self.offline_mode:
                heartbeat_payload = {
                    "node": "esp8266_mock",
                    "status": "ONLINE",
                    "simulated": True,
                    "angle": self.current_angle,
                    "mode": "SEARCHING" if self.is_searching else "TRACKING"
                }
                try:
                    self.client.publish(TOPIC_HEARTBEAT, json.dumps(heartbeat_payload))
                except Exception as e:
                    self.log(f"Failed to publish heartbeat: {e}")

        # 5. Redraw the canvas visualizer and labels
        self.draw_scene()
        self.update_labels()
        
        # Cycle back in 10ms for high-frequency time checking
        self.root.after(10, self.update_simulation)

    def update_labels(self):
        # Update text metrics dynamically
        self.angle_label.config(text=f"Servo Angle: {self.current_angle:.1f}°")
        
        if self.is_searching:
            mode_str = "System Mode: LOCAL SEARCH" if self.is_local_searching else "System Mode: FAST SEARCH"
            self.mode_label.config(text=mode_str, fg=self.accent_amber)
            self.wd_label.config(text="Face Watchdog: Active (sweeping)", fg="#cbd5e1")
        else:
            self.mode_label.config(text="System Mode: LOCKED & TRACKING", fg=self.accent_green)
            elapsed = time.time() - self.last_face_detect_time
            remaining = max(0.0, FACE_TIMEOUT - elapsed)
            self.wd_label.config(text=f"Face Watchdog: {remaining:.1f}s to timeout", fg=self.accent_amber)

        # Update command label
        cmd = getattr(self, "last_cmd", "NONE")
        if cmd in ("CENTERED", "TRACK"):
            self.command_label.config(text=f"Motor Cmd: {cmd}", fg=self.accent_green)
        elif cmd in ("MOVE_LEFT", "MOVE_RIGHT"):
            self.command_label.config(text=f"Motor Cmd: {cmd}", fg=self.accent_blue)
        elif cmd == "NO_FACE":
            self.command_label.config(text=f"Motor Cmd: {cmd}", fg=self.accent_red)
        else:
            self.command_label.config(text=f"Motor Cmd: {cmd}", fg="#cbd5e1")

    # --- 2D CANVAS DRAWING ENGINE ---
    def draw_scene(self):
        self.canvas.delete("all")
        
        # Center of the SG90 Servo body
        servo_cx = 180
        servo_cy = 240
        
        # 1. Draw grid lines for clean alignment background
        for x in range(0, self.canvas_width, 40):
            self.canvas.create_line(x, 0, x, self.canvas_height, fill="#1c1c1f", width=1)
        for y in range(0, self.canvas_height, 40):
            self.canvas.create_line(0, y, self.canvas_width, y, fill="#1c1c1f", width=1)
            
        # 2. Draw Field of View Cone (Shaded polygon)
        # Convert servo angle to polar coordinates on canvas (angle increases counter-clockwise)
        angle_rad = math.radians(self.current_angle)
        
        # FOV cone details (60 degrees total spread, length 160)
        cone_length = 160
        spread_deg = 30
        
        left_limit_rad = math.radians(self.current_angle - spread_deg)
        right_limit_rad = math.radians(self.current_angle + spread_deg)
        
        # Cone wedge vertices
        v0_x, v0_y = servo_cx, servo_cy
        v1_x = servo_cx + cone_length * math.cos(left_limit_rad)
        v1_y = servo_cy - cone_length * math.sin(left_limit_rad)
        v2_x = servo_cx + cone_length * math.cos(right_limit_rad)
        v2_y = servo_cy - cone_length * math.sin(right_limit_rad)
        
        # Green FOV Cone fill and outline
        self.canvas.create_polygon(
            v0_x, v0_y, v1_x, v1_y, v2_x, v2_y, 
            fill="#1b3a2b", outline=self.accent_green, 
            width=2, dash=(4, 2), stipple="gray25"
        )
        
        # 3. Draw physical SG90 Servo Motor
        # Blue servo body box
        self.canvas.create_rectangle(
            servo_cx - 40, servo_cy - 15, servo_cx + 40, servo_cy + 30, 
            fill="#0a84ff", outline="#004080", width=2
        )
        # Mounting wings
        self.canvas.create_rectangle(
            servo_cx - 55, servo_cy + 5, servo_cx - 40, servo_cy + 15, 
            fill="#0a84ff", outline="#004080", width=1
        )
        self.canvas.create_rectangle(
            servo_cx + 40, servo_cy + 5, servo_cx + 55, servo_cy + 15, 
            fill="#0a84ff", outline="#004080", width=1
        )
        # Screws in wings
        self.canvas.create_oval(servo_cx - 50, servo_cy + 8, servo_cx - 46, servo_cy + 12, fill="#8e8e93")
        self.canvas.create_oval(servo_cx + 46, servo_cy + 8, servo_cx + 50, servo_cy + 12, fill="#8e8e93")
        
        # Brass gear ring (center)
        self.canvas.create_oval(
            servo_cx - 12, servo_cy - 12, servo_cx + 12, servo_cy + 12, 
            fill="#bf9b30", outline="#8a6d1c", width=1
        )
        
        # 4. Draw Servo Horn & Webcam (Rotates with self.current_angle)
        # Horn endpoint calculations
        horn_len = 35
        hx = servo_cx + horn_len * math.cos(angle_rad)
        hy = servo_cy - horn_len * math.sin(angle_rad)
        
        # White Horn arm
        self.canvas.create_line(
            servo_cx, servo_cy, hx, hy, 
            fill="#f2f2f7", width=10, capstyle="round"
        )
        self.canvas.create_oval(
            servo_cx - 6, servo_cy - 6, servo_cx + 6, servo_cy + 6, 
            fill="#e5e5ea", outline="#3a3a3c", width=1
        )
        
        # Camera Module (draw a small dark rectangular block mounted at the tip of the horn)
        cam_w = 28
        cam_h = 10
        
        # Compute camera vertices rotated around the horn tip
        # Base vector perpendicular to horn: (dy, -dx)
        perp_x = -math.sin(angle_rad)
        perp_y = -math.cos(angle_rad)
        
        c1_x = hx + (cam_h/2)*math.cos(angle_rad) + (cam_w/2)*perp_x
        c1_y = hy - (cam_h/2)*math.sin(angle_rad) + (cam_w/2)*perp_y
        c2_x = hx + (cam_h/2)*math.cos(angle_rad) - (cam_w/2)*perp_x
        c2_y = hy - (cam_h/2)*math.sin(angle_rad) - (cam_w/2)*perp_y
        c3_x = hx - (cam_h/2)*math.cos(angle_rad) - (cam_w/2)*perp_x
        c3_y = hy + (cam_h/2)*math.sin(angle_rad) - (cam_w/2)*perp_y
        c4_x = hx - (cam_h/2)*math.cos(angle_rad) + (cam_w/2)*perp_x
        c4_y = hy + (cam_h/2)*math.sin(angle_rad) + (cam_w/2)*perp_y
        
        # Draw Camera body
        self.canvas.create_polygon(c1_x, c1_y, c2_x, c2_y, c3_x, c3_y, c4_x, c4_y, fill="#3a3a3c", outline="#2c2c2e")
        
        # Camera Lens (tiny blue circular aperture on the front side facing along the angle)
        lens_x = hx + (cam_h/2) * math.cos(angle_rad)
        lens_y = hy - (cam_h/2) * math.sin(angle_rad)
        self.canvas.create_oval(lens_x - 3, lens_y - 3, lens_x + 3, lens_y + 3, fill="#0a84ff", outline="#ffffff", width=1)
        
        # 5. Draw Draggable Face (Yellow circle representing target head)
        fx, fy = self.face_x, self.face_y
        r = 18
        
        # Check if face falls inside the FOV Cone boundaries
        dx = fx - servo_cx
        dy = servo_cy - fy
        dist_to_face = math.hypot(dx, dy)
        
        in_fov = False
        if dist_to_face <= cone_length:
            face_angle_rad = math.atan2(dy, dx)
            # Normalize angle relative to current servo angle
            angle_diff = math.degrees(face_angle_rad) - self.current_angle
            # Normalize diff to [-180, 180]
            angle_diff = (angle_diff + 180) % 360 - 180
            if abs(angle_diff) <= spread_deg:
                in_fov = True
                
        # Choose color based on detection/lock state
        face_color = self.accent_amber
        face_outline = "#d4af37"
        if in_fov:
            face_color = self.accent_green
            face_outline = "#1e823b"
            # Draw tracking locking lines (bounding box overlay)
            self.canvas.create_rectangle(fx - 24, fy - 24, fx + 24, fy + 24, outline=self.accent_green, width=1, dash=(2, 2))
            self.canvas.create_text(fx, fy - 35, text="LOCKED", fill=self.accent_green, font=("Plus Jakarta Sans", 8, "bold"))
        
        # Head Circle
        self.canvas.create_oval(fx - r, fy - r, fx + r, fy + r, fill=face_color, outline=face_outline, width=2)
        
        # Eyes
        self.canvas.create_oval(fx - 7, fy - 6, fx - 4, fy - 3, fill="#000000")
        self.canvas.create_oval(fx + 4, fy - 6, fx + 7, fy - 3, fill="#000000")
        
        # Smile or neutral mouth
        if in_fov:
            # Happy smiling mouth curve
            self.canvas.create_arc(fx - 8, fy - 2, fx + 8, fy + 8, start=180, extent=180, style="arc", outline="#000000", width=2)
        else:
            # Neutral line
            self.canvas.create_line(fx - 6, fy + 4, fx + 6, fy + 4, fill="#000000", width=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GUI ESP8266 and Servo hardware simulator.")
    parser.add_argument("--broker", type=str, default="157.173.101.159", help="MQTT Broker IP address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT Broker Port")
    args = parser.parse_args()
    
    root = tk.Tk()
    gui = HardwareSimulatorGUI(root, args.broker, args.port)
    root.mainloop()
