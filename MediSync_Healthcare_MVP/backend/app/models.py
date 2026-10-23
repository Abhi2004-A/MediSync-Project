from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))

class Prescription(Base):
    __tablename__ = "prescriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    medication_name: Mapped[str] = mapped_column(String(160))
    dosage: Mapped[str] = mapped_column(String(160))
    schedule: Mapped[str] = mapped_column(String(160), default="Morning and evening")
    instructions: Mapped[str] = mapped_column(Text, default="")
    start_date: Mapped[str] = mapped_column(String(10))
    end_date: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DoseLog(Base):
    __tablename__ = "dose_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prescription_id: Mapped[int] = mapped_column(ForeignKey("prescriptions.id"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    scheduled_for: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(String(300), default="")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
