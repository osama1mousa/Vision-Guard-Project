import cv2
import io
import requests
from config import API_URL

def draw_ui_box(frame, x1, y1, x2, y2, color, text):
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
    corner_len = 15; thick = 4
    cv2.line(frame, (x1, y1), (x1+corner_len, y1), color, thick)
    cv2.line(frame, (x1, y1), (x1, y1+corner_len), color, thick)
    cv2.line(frame, (x2, y1), (x2-corner_len, y1), color, thick)
    cv2.line(frame, (x2, y1), (x2, y1+corner_len), color, thick)
    cv2.line(frame, (x1, y2), (x1+corner_len, y2), color, thick)
    cv2.line(frame, (x1, y2), (x1, y2-corner_len), color, thick)
    cv2.line(frame, (x2, y2), (x2-corner_len, y2), color, thick)
    cv2.line(frame, (x2, y2), (x2-corner_len, y2), color, thick)
    
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 0.5, 1)[0]
    cv2.rectangle(frame, (x1, y1-text_size[1]-10), (x1+text_size[0]+10, y1), color, cv2.FILLED)
    text_color = (0, 0, 0) if color in [(0, 255, 255), (0, 255, 0)] else (255, 255, 255)
    cv2.putText(frame, text, (x1+5, y1-5), cv2.FONT_HERSHEY_DUPLEX, 0.5, text_color, 1)

def send_alert_to_server(threat_label, frame_copy):
    try:
        _, buffer = cv2.imencode('.jpg', frame_copy, [cv2.IMWRITE_JPEG_QUALITY, 90])
        io_buf = io.BytesIO(buffer)
        requests.post(f"{API_URL}/log_threat", files={"file": ("alert.jpg", io_buf, "image/jpeg")}, data={"threat_type": threat_label})
    except: pass

def log_person_access(person_name):
    try: requests.post(f"{API_URL}/log_access", data={"person_name": person_name})
    except: pass

def log_unified_session(session_id, category, identifier, start_time, end_time, duration):
    try:
        requests.post(f"{API_URL}/log_structured_item", json={
            "session_id": session_id,
            "category": category,
            "identifier": identifier,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration
        })
    except: pass