import cv2
import zmq
import numpy as np
import requests
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

SERVER_IP = "10.100.3.110"

class ZMQReceiver(QThread):
    frame_ready = pyqtSignal(QImage)
    connection_lost = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect("tcp://127.0.0.1:5555")
        socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        socket.setsockopt(zmq.CONFLATE, 1) 
        socket.setsockopt(zmq.RCVTIMEO, 2000)

        while self.running:
            try:
                frame_bytes = socket.recv()
                np_arr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if frame is not None:
                    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_image.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
                    self.frame_ready.emit(qt_image)
            except zmq.Again:
                self.connection_lost.emit()
            except Exception:
                pass

    def stop(self):
        self.running = False
        self.wait()

class APIWorker(QThread):
    logs_ready = pyqtSignal(list)

    def run(self):
        while True:
            try:
                recent_logs = []
                try:
                    alerts_req = requests.get(f"http://{SERVER_IP}:8000/api/alerts", timeout=1.0)
                    if alerts_req.status_code == 200:
                        for a in alerts_req.json():
                            cat = a.get("category")
                            ts = a.get("timestamp")
                            
                            if cat == "VERIFIED":
                                recent_logs.append((f"AUTHORIZED ENTRY: {a.get('person_name')}", "VERIFIED", ts))
                            elif cat == "UNAUTH":
                                recent_logs.append(("UNAUTHORIZED PERSON DETECTED", "UNAUTH", ts))
                            elif cat == "THREAT":
                                recent_logs.append((f"{a.get('threat_type')} DETECTED", "THREAT", ts))
                            elif cat == "SNAPSHOT":
                                recent_logs.append(("MANUAL SNAPSHOT TAKEN", "SNAPSHOT", ts))
                            else:
                                recent_logs.append((f"{a.get('threat_type')} DETECTED", "INFO", ts))
                except: pass

                self.logs_ready.emit(recent_logs[:100])
            except: pass
            self.msleep(2000)