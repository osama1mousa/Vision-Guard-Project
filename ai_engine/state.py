import threading

# ==========================================
# GLOBAL STATE & LOCKS
# ==========================================
shared_frame = None
yolo_boxes = []
face_boxes = []

frame_lock = threading.Lock()
box_lock = threading.Lock()

# Global flag for cntinuous alarm and warning overlay
threat_active = False