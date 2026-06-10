from sqlalchemy import Column, Integer, String, DateTime
import datetime
from database import Base, engine

class ThreatLog(Base):
    __tablename__ = "threat_logs"
    id = Column(Integer, primary_key=True, index=True)
    threat_type = Column(String)
    image_url = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.now)

class FaceLog(Base):
    __tablename__ = "face_logs"
    id = Column(Integer, primary_key=True, index=True)
    person_name = Column(String)
    status = Column(String) 
    image_url = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.now)

class SnapshotLog(Base):
    __tablename__ = "snapshot_logs"
    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.now)

Base.metadata.create_all(bind=engine)