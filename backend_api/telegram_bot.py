import requests

# 💡 ======= TELEGRAM SETTINGS ======= 💡
TELEGRAM_BOT_TOKEN = "8943979064:AAG0QpoZlMz4Sa2QBdQMGIpIo7tw5iP_HaU"
TELEGRAM_CHAT_ID = "847271786"
# ====================================================

def send_telegram_alert(threat_type: str, image_path: str, timestamp: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return 
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    caption = f"🚨 SECURITY ALERT 🚨\n\n⚠️ Threat Type: {threat_type}\n🕒 Time: {timestamp}\n🛡️ System: VisionGuard"
    
    try:
        with open(image_path, "rb") as image_file:
            requests.post(
                url, 
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, 
                files={"photo": image_file}
            )
    except Exception as e:
        print(f"Telegram Error: {e}")