import torch

# ==========================================
# SERVER & DEVICE CONFIGURATION
# ==========================================
SERVER_IP = "10.100.3.110" 
SERVER_PORT = "8000"
API_URL = f"http://{SERVER_IP}:{SERVER_PORT}/api"

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

# ==========================================
# AI SETTINGS & THRESHOLDS
# ==========================================
TARGET_CLASSES = [
    24,  # backpack (BAG)
    26,  # handbag (BAG)
    43   # knife
]

CONF_PISTOL = 0.73
CONF_KNIFE = 0.35
CONF_BAG = 0.60     
FACE_TOLERANCE = 0.52 

# ==========================================
# SECURITY ZONES & TIME SETTINGS
# ==========================================
WORK_START_HOUR = 8
WORK_END_HOUR = 23