from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import datetime
import os
import json

from database import get_db
from models import ThreatLog, FaceLog, SnapshotLog
from telegram_bot import send_telegram_alert

app = FastAPI(title="VisionGuard API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

if not os.path.exists("static/alerts"): os.makedirs("static/alerts")
if not os.path.exists("static/snapshots"): os.makedirs("static/snapshots")
app.mount("/static", StaticFiles(directory="static"), name="static")

transient_info_logs = []
CACHE_FILE = "session_logs.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f: return json.load(f)
        except: pass
    return []

def save_cache(data):
    with open(CACHE_FILE, "w") as f: json.dump(data, f)

structured_report_cache = load_cache()

@app.post("/api/log_threat")
async def log_threat(
    background_tasks: BackgroundTasks, 
    threat_type: str = Form(...), 
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    t_type = threat_type.upper()
    now_time = datetime.datetime.now()

    if t_type not in ["WEAPON", "PISTOL", "KNIFE", "UNAUTHORIZED", "OUT_OF_HOURS_INTRUSION"]:
        transient_info_logs.append({
            "threat_type": t_type,
            "timestamp": now_time.strftime("%Y-%m-%d %H:%M:%S"),
            "category": "INFO"
        })
        if len(transient_info_logs) > 30:
            transient_info_logs.pop(0)
        return {"status": "Object sent to UI live feed (Not saved to DB)"}

    file_name = f"{now_time.strftime('%H%M%S')}_{file.filename}"
    file_path = f"static/alerts/{file_name}"
    with open(file_path, "wb") as buffer: 
        buffer.write(await file.read())
    
    if t_type in ["WEAPON", "PISTOL", "KNIFE"]:
        db.add(ThreatLog(threat_type=t_type, image_url=f"/static/alerts/{file_name}"))
        background_tasks.add_task(send_telegram_alert, t_type, file_path, now_time.strftime("%Y-%m-%d %H:%M:%S"))
        
    elif t_type == "UNAUTHORIZED":
        db.add(FaceLog(person_name="UNKNOWN", status="UNAUTHORIZED", image_url=f"/static/alerts/{file_name}"))
        
    elif t_type == "OUT_OF_HOURS_INTRUSION":
        db.add(FaceLog(person_name="UNKNOWN", status="OUT_OF_HOURS_INTRUSION", image_url=f"/static/alerts/{file_name}"))
        background_tasks.add_task(send_telegram_alert, "AFTER-HOURS INTRUSION", file_path, now_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    db.commit()
    return {"status": "Threat/Unauth Logged securely to DB and Telegram"}

@app.post("/api/log_access")
async def log_access(person_name: str = Form(...), db: Session = Depends(get_db)):
    db.add(FaceLog(person_name=person_name, status="AUTHORIZED", image_url=""))
    db.commit()
    return {"status": "Access Logged successfully", "person": person_name}

@app.post("/api/snapshot")
async def take_snapshot(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_name = f"SNAP_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    file_path = f"static/snapshots/{file_name}"
    with open(file_path, "wb") as buffer: 
        buffer.write(await file.read())
    db.add(SnapshotLog(image_url=f"/static/snapshots/{file_name}"))
    db.commit()
    return {"status": "Snapshot saved"}

@app.get("/api/alerts")
def get_alerts(db: Session = Depends(get_db)):
    logs = []
    for t in db.query(ThreatLog).order_by(ThreatLog.timestamp.desc()).limit(20).all():
        logs.append({"threat_type": t.threat_type, "timestamp": t.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "category": "THREAT"})
    for f in db.query(FaceLog).order_by(FaceLog.timestamp.desc()).limit(20).all():
        if f.status == "UNAUTHORIZED":
            logs.append({"threat_type": "UNAUTHORIZED", "timestamp": f.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "category": "UNAUTH"})
        elif f.status == "OUT_OF_HOURS_INTRUSION":
            logs.append({"threat_type": "OUT OF HOURS INTRUSION", "timestamp": f.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "category": "OUT_OF_HOURS"})
        else:
            logs.append({"person_name": f.person_name, "timestamp": f.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "category": "VERIFIED"})
    for s in db.query(SnapshotLog).order_by(SnapshotLog.timestamp.desc()).limit(10).all():
        logs.append({"threat_type": "MANUAL SNAPSHOT", "timestamp": s.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "category": "SNAPSHOT"})
    
    logs.extend(transient_info_logs)
    return sorted(logs, key=lambda x: x["timestamp"], reverse=True)

@app.post("/api/log_structured_item")
async def log_structured_item(item: dict):
    global structured_report_cache
    session_id = item.get("session_id")
    
    updated = False
    if session_id:
        for idx, existing_item in enumerate(structured_report_cache):
            if existing_item.get("session_id") == session_id:
                structured_report_cache[idx] = item
                updated = True
                break
                
    if not updated:
        if "detection_time" not in item:
            item["detection_time"] = datetime.datetime.now().strftime("%H:%M:%S")
        structured_report_cache.append(item)
        
    save_cache(structured_report_cache)
    return {"status": "success", "cached_items_count": len(structured_report_cache)}

@app.get("/api/structured_logs")
def get_structured_logs():
    return structured_report_cache

try:
    from report_generator import generate_pdf_report
    @app.get("/api/generate_report")
    def trigger_report_generation(period: str = "daily"):
        success = generate_pdf_report(report_period=period.lower().strip())
        return {"status": "success" if success else "error"}
except ImportError:
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)