import argparse
import time
import sys
import cv2
import numpy as np
import os
import csv
from collections import defaultdict, deque
from ultralytics import YOLO
from datetime import datetime
import requests
import threading

DEFAULT_VERIFY_DURATION = 2.0
DEFAULT_GRACE_PERIOD = 0.5  # Time to hold overlay after object lost
DEFAULT_SMOOTH_ALPHA = 0.6  # EMA Alpha (High = more responsive, Low = smoother)
DEFAULT_EXPAND_RATIO = 0.30 # 30% expansion

CLASS_MAPPING_INDO = {
    39: "Botol", 41: "Gelas", 42: "Garpu", 43: "Pisau", 44: "Sendok", 45: "Mangkok",
    46: "Pisang", 47: "Apel", 48: "Sandwich", 49: "Jeruk", 50: "Brokoli", 51: "Wortel",
    52: "Hot Dog", 53: "Pizza", 54: "Donat", 55: "Kue",
    67: "Hape", 64: "Mouse", 63: "Laptop", 66: "Keyboard", 76: "Gunting",
    73: "Buku", 74: "Jam", 75: "Vas", 77: "Teddy Bear", 62: "TV"
}

CATEGORY_MAPPING = {
    "non_organic": [
        39, 41, 42, 43, 44, 45,
        67, 64, 63, 66, 76, 62, 74,
        73, 75
    ],
    "organic": [
        46, 47, 48, 49, 50, 51, 52, 53, 54, 55
    ]
}

# Invert for O(1) lookup
CLASS_TO_CATEGORY = {}
for cat, ids in CATEGORY_MAPPING.items():
    for cid in ids:
        CLASS_TO_CATEGORY[cid] = cat

class BBoxSmoother:
    def __init__(self, alpha=0.6):
        self.alpha = alpha
        self.tracks = {} 
    def update(self, tid, box):
        if tid not in self.tracks:
            self.tracks[tid] = box
            return box
        
        prev = self.tracks[tid]
        new_box = [
            self.alpha * box[0] + (1 - self.alpha) * prev[0],
            self.alpha * box[1] + (1 - self.alpha) * prev[1],
            self.alpha * box[2] + (1 - self.alpha) * prev[2],
            self.alpha * box[3] + (1 - self.alpha) * prev[3]
        ]
        self.tracks[tid] = new_box
        return new_box
    
    def cleanup(self, current_tids):
        to_del = [tid for tid in self.tracks if tid not in current_tids]
        for tid in to_del:
            del self.tracks[tid]

class CSVLogger:
    def __init__(self, path):
        self.path = path
        self.enabled = path is not None
        if self.enabled:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            self._init_file()

    def _init_file(self):
        if not os.path.exists(self.path):
            try:
                with open(self.path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['timestamp', 'track_id', 'label', 'conf', 'det_name', 'status'])
            except Exception as e:
                print(f"[LOG] Error creating log file: {e}")

    def log(self, track_id, label, conf, det_name, status):
        if not self.enabled: return
        try:
            with open(self.path, 'a', newline='') as f:
                writer = csv.writer(f)
                timestamp = datetime.now().isoformat()
                writer.writerow([timestamp, track_id, label, f"{conf:.2f}", det_name, status])
        except Exception as e:
            print(f"[LOG] Write error: {e}")

def parse_args():
    parser = argparse.ArgumentParser(description="Smart Waste Bin - Improved Detection")
    
    # Model
    parser.add_argument("--det-model", type=str, default="yolov8n.pt", help="Use COCO model for robustness")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.45)
    
    # Connection / Mode
    parser.add_argument("--mode", type=str, choices=['webcam', 'esp32cam'], default='webcam')
    parser.add_argument("--esp32cam-ip", type=str, help="IP of ESP32 for stream/control")
    parser.add_argument("--source", type=str, default=None)
    parser.add_argument("--devkit-ip", type=str, help="Target for HTTP control")
    parser.add_argument("--cam-ip", type=str, help="Alias for esp32cam-ip")
    
    parser.add_argument("--num-source", type=int, default=0, help="Numeric source index if webcam")
    parser.add_argument("--no-send", action='store_true')
    parser.add_argument("--send-timeout", type=float, default=3.0)

    # Features
    parser.add_argument("--ignore-person", type=str, default="true")
    parser.add_argument("--single-object", type=str, default="true")
    parser.add_argument("--expand", type=float, default=0.30)
    parser.add_argument("--smooth-alpha", type=float, default=0.6)
    parser.add_argument("--log-csv", type=str, default="logs/history.csv")

    args = parser.parse_args()
    
    # Handle aliases
    if args.cam_ip and not args.esp32cam_ip:
        args.esp32cam_ip = args.cam_ip
        
    # Auto-Switch Mode if IP is provided
    if args.esp32cam_ip and args.mode == 'webcam':
         args.mode = 'esp32cam'
    
    # Bool corrections
    args.ignore_person = args.ignore_person.lower() == "true"
    args.single_object = args.single_object.lower() == "true"
    
    # Auto-config logic
    if args.mode == 'esp32cam':
        # Default devkit-ip if not set (Single Board Assumption)
        if args.esp32cam_ip and not args.devkit_ip:
             args.devkit_ip = args.esp32cam_ip
             
        if not args.esp32cam_ip and not args.source:
             print("Error: --mode esp32cam requires --esp32cam-ip")
             sys.exit(1)
        if args.esp32cam_ip:
            if not args.source: args.source = f"http://{args.esp32cam_ip}:81/stream"
            if not args.devkit_ip: args.devkit_ip = args.esp32cam_ip
    elif args.mode == 'webcam':
        if not args.source: 
             # Use generic source if provided, else use num-source
             args.source = str(args.num_source)
        
    return args

def main():
    args = parse_args()
    
    # Init Camera
    print(f"Opening source: {args.source}")
    
    # Increase FFMPEG timeout/attempts via environment variables
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp|timeout;5000000" # 5s timeout
    os.environ["OPENCV_FFMPEG_READ_ATTEMPTS"] = "10000" # More attempts

    def open_video_stream(source):
        # Explicitly use FFMPEG for network streams to handle timeouts better
        if isinstance(source, str) and source.startswith('http'):
            # Force FFMPEG backend
            cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
            # Set buffer size to 0 to reduce latency (important for MJPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 0)
        else:
            # Webcam or file
            if isinstance(source, str) and source.isdigit():
                 source = int(source)
            cap = cv2.VideoCapture(source)
            
        if not cap.isOpened():
            print(f"Failed to open video source: {source}")
            return None
        return cap

    cap = open_video_stream(args.source)
    if cap is None:
        return

    # Init Model
    print(f"Loading Model: {args.det_model}")
    model = YOLO(args.det_model)
    
    # Init Helpers
    smoother = BBoxSmoother(alpha=args.smooth_alpha)
    logger = CSVLogger(args.log_csv)
    
    # State
    track_state = {}     # {tid: {'first_seen': time, 'label': str, 'confirmed': bool}}
    last_sent_time = 0
    net_status = "IDLE"
    ignored_person_count = 0
    
    print("System READY. Press 'q' to exit.")
    
    # Enable Resizable Window (Fullscreen support)
    cv2.namedWindow("Smart Waste - Improved", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Smart Waste - Improved", 1280, 720) # Set default big size

    # Main Loop
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Stream lost... retrying")
            time.sleep(1)
            cap.release()
            
            # Reconnect
            cap = open_video_stream(args.source)
            if cap is None:
                continue
                
            continue
            
        h, w = frame.shape[:2]
        current_time = time.time()
        
        # Inference
        results = model.track(frame, persist=True, conf=args.conf, iou=args.iou, verbose=False, tracker="botsort.yaml")
        
        candidates = []
        current_tids = []
        ignored_person_count = 0
        
        if results and results[0].boxes and results[0].boxes.id is not None:
            boxes = results[0].boxes
            track_ids = boxes.id.cpu().numpy().astype(int)
            clss = boxes.cls.cpu().numpy().astype(int)
            confs = boxes.conf.cpu().numpy()
            xyxys = boxes.xyxy.cpu().numpy()
            
            for i, (tid, cls_id, conf, xyxy) in enumerate(zip(track_ids, clss, confs, xyxys)):
                # 1. Ignore Person
                if cls_id == 0: # 0 is Person in COCO
                    if args.ignore_person:
                        ignored_person_count += 1
                        continue
                
                # 2. Filter Unknown/Irrelevant (Only allow mapped classes)
                if cls_id not in CLASS_TO_CATEGORY:
                    continue
                    
                current_tids.append(tid)
                
                area = (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1])
                candidates.append({
                    'tid': tid,
                    'cls_id': cls_id,
                    'conf': conf,
                    'box_raw': xyxy,
                    'area': area
                })
        
        smoother.cleanup(current_tids)
        
        target = None
        
        # 3. Single Object Selection
        if candidates:
            if args.single_object:
                # Simple Heuristic: Largest Area
                # Could assume center bias later if needed
                target = max(candidates, key=lambda x: x['area'])
            else:
                # Pick largest for main display focus in multi mode too for now
                target = max(candidates, key=lambda x: x['area'])
        
        # UI Drawing
        if target:
            tid = target['tid']
            cls_id = target['cls_id']
            box_raw = target['box_raw'] # [x1, y1, x2, y2]
            
            # 4. Smoothing
            box_smooth = smoother.update(tid, box_raw)
            bx1, by1, bx2, by2 = map(int, box_smooth)
            
            # 5. Expansion
            bw = bx2 - bx1
            bh = by2 - by1
            pad_w = int(bw * args.expand / 2)
            pad_h = int(bh * args.expand / 2)
            
            x1 = max(0, bx1 - pad_w)
            y1 = max(0, by1 - pad_h)
            x2 = min(w, bx2 + pad_w)
            y2 = min(h, by2 + pad_h)
            
            # Logic & State Update
            det_name_indo = CLASS_MAPPING_INDO.get(cls_id, model.names[cls_id])
            category = CLASS_TO_CATEGORY.get(cls_id, "unknown")
            
            if tid not in track_state:
                track_state[tid] = {
                    'first_seen': current_time,
                    'label': category,
                    'last_seen': current_time,
                    'confirmed': False
                }
            else:
                track_state[tid]['last_seen'] = current_time
            
            st = track_state[tid]
            duration = current_time - st['first_seen']
            
            status_text = "VERIFYING"
            color = (0, 255, 255) # Yellow
            
            if duration > DEFAULT_VERIFY_DURATION:
                status_text = "CONFIRMED"
                color = (0, 255, 0) # Green
                
                # 6. Sending (Once per confirmed session, or throttled)
                # 6. Sending (Once per confirmed session, or throttled)
                if not st['confirmed']:
                    # Send now
                    if args.devkit_ip and not args.no_send:
                        url = f"http://{args.devkit_ip}/label?value={category}"
                        
                        def send_thread(target_url, timeout):
                            try:
                                # print(f"Sending {target_url}")
                                requests.get(target_url, timeout=timeout)
                                print(f"CMD Sent: {target_url}")
                            except Exception as e:
                                print(f"Net Error: {e}")

                        # Run in background thread
                        t = threading.Thread(target=send_thread, args=(url, args.send_timeout))
                        t.daemon = True # Kill thread if main exits
                        t.start()
                        
                        net_status = "SENDING..."
                        st['confirmed'] = True
                        logger.log(tid, category, target['conf'], det_name_indo, "Sent")
                    else:
                        # Simulation Mode Log
                        net_status = "SIM-OK"
                        st['confirmed'] = True
                        logger.log(tid, category, target['conf'], det_name_indo, "Simulation-Sent")

            
            # Draw Box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw Label (Name + Cat)
            label_display = f"{det_name_indo} ({category})"
            t_size = cv2.getTextSize(label_display, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            cv2.rectangle(frame, (x1, y1-30), (x1+t_size[0]+10, y1), color, -1)
            cv2.putText(frame, label_display, (x1+5, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 2)
            
        else:
            # No target
            pass
            
        # Global Overlay
        # Top Bar
        # Global Overlay
        # Top Bar (Dedicated Area)
        # Add 40px black border at top so text doesn't cover video
        border_h = 40
        frame = cv2.copyMakeBorder(frame, border_h, 0, 0, 0, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        
        info_x = 10
        # Reduced Font Scale: 1.2 -> 0.8
        cv2.putText(frame, f"MODE: {'SINGLE' if args.single_object else 'MULTI'} | EXPAND: {int(args.expand*100)}%", (info_x, 25), cv2.FONT_HERSHEY_PLAIN, 1.0, (200, 200, 200), 1)
        
        ignored_text = ""
        if ignored_person_count > 0:
            ignored_text = f" | IG: {ignored_person_count}"
        
        # Draw on video area (shifted down by border_h?? No, copyMakeBorder shifts image down)
        # But we want text in the border. Border is at y=0 to y=40.
        
        # Small Info
        cv2.putText(frame, f"SRC: {args.source}{ignored_text}", (info_x, 15 + 20), cv2.FONT_HERSHEY_PLAIN, 0.8, (150, 150, 150), 1) # This effectively overlays top of video if line 2
        
        # Re-draw top line cleanly
        # Let's simple put everything in the top border
        
        curr_fps = 1.0 / (time.time() - current_time + 0.0001)
        # Right Side Info
        cv2.putText(frame, f"FPS: {int(curr_fps)}", (w - 80, 28), cv2.FONT_HERSHEY_PLAIN, 1.2, (0, 255, 0), 1)
        
        net_col = (0, 255, 0) if net_status == "OK" or net_status == "SIM-OK" else (0, 0, 255)
        # Condensed Net Status
        cv2.putText(frame, net_status, (w - 200, 28), cv2.FONT_HERSHEY_PLAIN, 1.0, net_col, 1)

        cv2.imshow("Smart Waste - Improved", frame)
        
        # Exit on 'q' or Window 'X' button
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        if cv2.getWindowProperty("Smart Waste - Improved", cv2.WND_PROP_VISIBLE) < 1:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
