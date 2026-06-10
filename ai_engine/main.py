import os
# --- GPU CUDA INITIALIZATION ---
os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin")
# -------------------------------

import sys
import io
import time
import threading
import gc
import cv2
import zmq
import winsound

import state
from utils import draw_ui_box
from workers import camera_worker, yolo_worker, face_worker

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("\n" + "="*55)
print("  VISION GUARD - MODULAR AI ENGINE")
print("="*55)

# ==========================================
# BACKGROUND MAINTENANCE WORKERS
# ==========================================
def memory_cleaner_worker():
    while True:
        time.sleep(15)
        gc.collect()

def continuous_alarm_worker():
    while True:
        if state.threat_active:
            winsound.Beep(1200, 400)
            time.sleep(0.1)
        else:
            time.sleep(0.5)

# Start background maintenance
threading.Thread(target=memory_cleaner_worker, daemon=True).start()
threading.Thread(target=continuous_alarm_worker, daemon=True).start()

# Start core AI workers
threading.Thread(target=camera_worker, daemon=True).start()
threading.Thread(target=yolo_worker, daemon=True).start()
threading.Thread(target=face_worker, daemon=True).start()

# ==========================================
# ZERO MQ BROADCASTER (MAIN THREAD)
# ==========================================
print("✅ AI ENGINE READY - STREAMING 1080p @ 60FPS TO UI...")

context = zmq.Context()
zmq_socket = context.socket(zmq.PUB)
zmq_socket.bind("tcp://127.0.0.1:5555")

try:
    while True:
        loop_start = time.time()
        
        with state.frame_lock:
            if state.shared_frame is None:
                time.sleep(0.01)
                continue
            display_frame = state.shared_frame.copy()

        with state.box_lock:
            current_boxes = state.yolo_boxes + state.face_boxes

        if state.threat_active:
            cv2.rectangle(display_frame, (0, 0), (display_frame.shape[1], display_frame.shape[0]), (0, 0, 255), 15)
            if int(time.time() * 4) % 2 == 0:
                cv2.putText(display_frame, " CRITICAL THREAT DETECTED ", (display_frame.shape[1]//2 - 350, 100), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 0, 255), 3)

        for (x1, y1, x2, y2, color, text) in current_boxes:
            draw_ui_box(display_frame, x1, y1, x2, y2, color, text)

        _, local_buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        zmq_socket.send(local_buffer.tobytes())
            
        elapsed = time.time() - loop_start
        time.sleep(max(0, 0.016 - elapsed))
        
except KeyboardInterrupt:
    print("\n  Shutting down Modular AI Engine...")