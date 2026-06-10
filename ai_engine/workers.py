import os
import time
import threading
import datetime
import cv2
import numpy as np
import face_recognition
import uuid  
from ultralytics import YOLO
import state
from config import DEVICE, CONF_PISTOL, CONF_KNIFE, CONF_BAG, TARGET_CLASSES, FACE_TOLERANCE, WORK_START_HOUR, WORK_END_HOUR
from utils import send_alert_to_server, log_person_access, draw_ui_box, log_unified_session

# ==========================================
# 1. CAMERA THREAD
# ==========================================
def camera_worker():
    print(" Initializing Sony A7III Stream (1080p @ 30Hz)...")
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW) 
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv2.CAP_PROP_FPS, 30)  
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    while True:
        ret, frame = cap.read()
        if ret:
            with state.frame_lock:
                state.shared_frame = frame
        else:
            time.sleep(0.005)

# ==========================================
# 2. YOLO WORKER (Threat Detection & Session Tracking)
# ==========================================
def yolo_worker():
    print("Loading YOLO Models...")
    gun_model = YOLO('pistol.pt').to(DEVICE)
    obj_model = YOLO('yolov8s.pt').to(DEVICE)
    
    active_objects = {} 
    
    while True:
        try:
            start_time = time.time()
            with state.frame_lock:
                if state.shared_frame is None:
                    time.sleep(0.01)
                    continue
                frame_ai = state.shared_frame.copy()
                
            temp_boxes = []
            detected_labels = set()

            pistol_results = gun_model(frame_ai, stream=True, verbose=False, device=DEVICE, conf=CONF_PISTOL, iou=0.45, agnostic_nms=True)
            for r in pistol_results:
                for box in r.boxes:
                    temp_boxes.append((*map(int, box.xyxy[0]), (0, 0, 255), f"WEAPON {float(box.conf[0]):.2f}"))
                    detected_labels.add("WEAPON")

            model_conf = min(CONF_KNIFE, CONF_BAG)
            object_results = obj_model(frame_ai, stream=True, verbose=False, device=DEVICE, classes=TARGET_CLASSES, conf=model_conf, iou=0.45, agnostic_nms=True)
            for r in object_results:
                for box in r.boxes:
                    label = obj_model.names[int(box.cls[0])].upper()
                    if label in ["BACKPACK", "HANDBAG"]: label = "BAG"
                    
                    if label == "KNIFE" and float(box.conf[0]) >= CONF_KNIFE:
                        temp_boxes.append((*map(int, box.xyxy[0]), (0, 0, 255), f"WEAPON {float(box.conf[0]):.2f}"))
                        detected_labels.add("WEAPON")
                    elif label == "BAG" and float(box.conf[0]) >= CONF_BAG:
                        temp_boxes.append((*map(int, box.xyxy[0]), (255, 0, 0), f"BAG {float(box.conf[0]):.2f}"))
                        detected_labels.add("BAG")

            with state.box_lock:
                state.yolo_boxes = temp_boxes
            state.threat_active = "WEAPON" in detected_labels

            now_dt = datetime.datetime.now()
            
            for t_label in detected_labels:
                if t_label not in active_objects:
                    active_objects[t_label] = {
                        "start_time": now_dt, 
                        "last_seen": now_dt, 
                        "session_id": uuid.uuid4().hex,
                        "alert_sent": False
                    }
                else:
                    active_objects[t_label]["last_seen"] = now_dt

            for t_label, session in active_objects.items():
                if not session["alert_sent"]:
                    session["alert_sent"] = True 
                    
                    alert_frame = frame_ai.copy()
                    with state.box_lock:
                        for (x1, y1, x2, y2, c, t) in state.yolo_boxes + state.face_boxes:
                            draw_ui_box(alert_frame, x1, y1, x2, y2, c, t)
                    threading.Thread(target=send_alert_to_server, args=(t_label, alert_frame), daemon=True).start()

                    if t_label == "WEAPON":
                        start_str = session["start_time"].strftime("%Y-%m-%d %H:%M:%S")
                        threading.Thread(target=log_unified_session, args=(session["session_id"], "THREAT", t_label, start_str, "Ongoing...", "Active"), daemon=True).start()

            expired_objects = []
            for t_label, session in active_objects.items():
                if (now_dt - session["last_seen"]).total_seconds() > 5:
                    expired_objects.append(t_label)
                    
                    if t_label == "WEAPON":
                        duration_secs = int((session["last_seen"] - session["start_time"]).total_seconds())
                        duration_str = f"{duration_secs//60}m {duration_secs%60}s" if duration_secs >= 60 else f"{duration_secs}s"
                        start_str = session["start_time"].strftime("%Y-%m-%d %H:%M:%S")
                        end_str = session["last_seen"].strftime("%Y-%m-%d %H:%M:%S")
                        threading.Thread(target=log_unified_session, args=(session["session_id"], "THREAT", t_label, start_str, end_str, duration_str), daemon=True).start()

            for t_label in expired_objects: del active_objects[t_label]

            elapsed = time.time() - start_time
            time.sleep(max(0, 0.033 - elapsed))  
            
        except Exception as e:
            print(f" YOLO THREAD CRASHED: {e}")
            time.sleep(1)

# ==========================================
# 3. FACE RECOGNITION (Session Tracking)
# ==========================================
def face_worker():
    known_encodings, known_names = [], []
    if os.path.exists('faces'):
        for person_name in os.listdir('faces'):
            person_folder = os.path.join('faces', person_name)
            if os.path.isdir(person_folder):
                for img_name in os.listdir(person_folder):
                    try: 
                        img = cv2.imread(os.path.join(person_folder, img_name))
                        encs = face_recognition.face_encodings(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                        if encs:
                            known_encodings.append(encs[0])
                            known_names.append(person_name)
                    except: continue

    active_sessions = {}
 
    while True:
        try:
            start_time = time.time()
            with state.frame_lock:
                if state.shared_frame is None:
                    time.sleep(0.01)
                    continue
                frame_ai = state.shared_frame.copy()

            rgb_small = cv2.cvtColor(cv2.resize(frame_ai, (0, 0), fx=0.50, fy=0.50), cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_small, number_of_times_to_upsample=2, model="hog")
            face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
            
            temp_boxes, detected_this_frame = [], set()
            
            current_hour = datetime.datetime.now().hour
            start_h = int(WORK_START_HOUR)
            end_h = int(WORK_END_HOUR)
            if start_h <= end_h:
                is_working_hours = start_h <= current_hour < end_h
            else:
                is_working_hours = current_hour >= start_h or current_hour < end_h
            is_out_of_hours = not is_working_hours
            
            for i, face_encoding in enumerate(face_encodings):
                real_name = "UNKNOWN"
                
                if is_out_of_hours:
                    display_text, color = "UNAUTHORIZED", (0, 0, 255)  
                else:
                    display_text, color = "UNAUTHORIZED", (0, 255, 255) 
                
                if known_encodings:
                    distances = face_recognition.face_distance(known_encodings, face_encoding)
                    if len(distances) > 0 and face_recognition.compare_faces(known_encodings, face_encoding, tolerance=FACE_TOLERANCE)[np.argmin(distances)]:
                        real_name = known_names[np.argmin(distances)].upper()
                        if is_out_of_hours:
                            display_text, color = f"THREAT: {real_name} (OUT OF HOURS)", (0, 0, 255)
                        else:
                            display_text, color = "AUTHORIZED", (0, 255, 0)
                
                detected_this_frame.add(real_name)
                top, right, bottom, left = face_locations[i]
                temp_boxes.append((left*2, top*2, right*2, bottom*2, color, display_text))
                
            with state.box_lock: state.face_boxes = temp_boxes

            now_dt = datetime.datetime.now()
            
            for name in detected_this_frame:
                if name not in active_sessions:
                    active_sessions[name] = {
                        "start_time": now_dt, 
                        "last_seen": now_dt, 
                        "is_out_of_hours": is_out_of_hours,
                        "session_id": uuid.uuid4().hex,
                        "alert_sent": False
                    }
                else:
                    active_sessions[name]["last_seen"] = now_dt

            for name, session in active_sessions.items():
                if not session["alert_sent"]:
                    session["alert_sent"] = True 
                    
                    category = "AFTER_HOURS" if session["is_out_of_hours"] else ("UNAUTHORIZED" if name == "UNKNOWN" else "AUTHORIZED")
                    start_str = session["start_time"].strftime("%Y-%m-%d %H:%M:%S")
                    
                    threading.Thread(target=log_unified_session, args=(session["session_id"], category, name, start_str, "Ongoing...", "Active"), daemon=True).start()

                    if session["is_out_of_hours"] or name == "UNKNOWN":
                        alert_label = "OUT_OF_HOURS_INTRUSION" if session["is_out_of_hours"] else "UNAUTHORIZED"
                        alert_frame = frame_ai.copy()
                        with state.box_lock:
                            for (x1, y1, x2, y2, c, t) in state.yolo_boxes + state.face_boxes:
                                draw_ui_box(alert_frame, x1, y1, x2, y2, c, t)
                        threading.Thread(target=send_alert_to_server, args=(alert_label, alert_frame), daemon=True).start()
                    else:
                        threading.Thread(target=log_person_access, args=(name,), daemon=True).start()

            expired_sessions = []
            for name, session in active_sessions.items():
                if (now_dt - session["last_seen"]).total_seconds() > 5: 
                    expired_sessions.append(name)
                    
                    duration_secs = int((session["last_seen"] - session["start_time"]).total_seconds())
                    duration_str = f"{duration_secs//3600}h {(duration_secs%3600)//60}m" if duration_secs >= 3600 else f"{duration_secs//60}m {duration_secs%60}s" if duration_secs >= 60 else f"{duration_secs}s"
                    
                    start_str = session["start_time"].strftime("%Y-%m-%d %H:%M:%S")
                    end_str = session["last_seen"].strftime("%Y-%m-%d %H:%M:%S")
                    
                    category = "AFTER_HOURS" if session["is_out_of_hours"] else ("UNAUTHORIZED" if name == "UNKNOWN" else "AUTHORIZED")
                    threading.Thread(target=log_unified_session, args=(session["session_id"], category, name, start_str, end_str, duration_str), daemon=True).start()

            for name in expired_sessions: del active_sessions[name]
                
            elapsed = time.time() - start_time
            time.sleep(max(0, 0.033 - elapsed))  
            
        except Exception as e:
            print(f" FACE THREAD CRASHED: {e}")
            time.sleep(1)