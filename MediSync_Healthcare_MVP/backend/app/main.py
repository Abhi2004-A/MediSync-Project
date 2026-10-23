import os
from datetime import date, datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .db import Base, engine, Session as SessionLocal, get_db
from .models import User, Prescription, DoseLog, AuditLog

app = FastAPI(title="MediSync API", description="Hackathon prototype; not for clinical use")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173","http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])
SECRET = os.getenv("JWT_SECRET_KEY", "DEMO-SECRET-CHANGE-BEFORE-DEPLOYMENT")
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

class LoginIn(BaseModel):
    email: EmailStr
    password: str
class PrescriptionIn(BaseModel):
    patient_email: EmailStr
    medication_name: str = Field(min_length=1, max_length=160)
    dosage: str = Field(min_length=1, max_length=160)
    schedule: str = "Morning and evening"
    instructions: str = ""
    start_date: str
    end_date: str
class StatusIn(BaseModel):
    status: str
class DoseIn(BaseModel):
    scheduled_for: str
    status: str
    note: str = ""
class SafetyIn(BaseModel):
    medication_names: list[str]

def token_for(u):
    return jwt.encode({"sub":str(u.id),"role":u.role,"exp":datetime.utcnow()+timedelta(hours=8)}, SECRET, algorithm="HS256")

def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    if not creds: raise HTTPException(401, "Sign in required")
    try: uid = int(jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])["sub"])
    except (JWTError, ValueError, KeyError): raise HTTPException(401, "Invalid or expired token")
    u = db.get(User, uid)
    if not u: raise HTTPException(401, "User unavailable")
    return u

def role_required(role):
    def check(u: User = Depends(current_user)):
        if u.role != role: raise HTTPException(403, f"{role.title()} role required")
        return u
    return check

def log(db, u, action, details=""):
    db.add(AuditLog(actor_id=u.id, action=action, details=details)); db.commit()

def serialize(p, db):
    patient, doctor = db.get(User,p.patient_id), db.get(User,p.doctor_id)
    return {"id":p.id,"patient_id":p.patient_id,"doctor_id":p.doctor_id,"patient_name":patient.name,
      "patient_email":patient.email,"doctor_name":doctor.name,"medication_name":p.medication_name,
      "dosage":p.dosage,"schedule":p.schedule,"instructions":p.instructions,"start_date":p.start_date,
      "end_date":p.end_date,"status":p.status,"created_at":p.created_at.isoformat()}

@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        doc = db.query(User).filter_by(email="doctor@medisync.demo").first()
        pat = db.query(User).filter_by(email="patient@medisync.demo").first()
        if not doc:
            doc=User(name="Dr. Demo",email="doctor@medisync.demo",password_hash=pwd.hash("Doctor123!"),role="doctor"); db.add(doc)
        if not pat:
            pat=User(name="Alex Patient",email="patient@medisync.demo",password_hash=pwd.hash("Patient123!"),role="patient"); db.add(pat)
        db.commit(); db.refresh(doc); db.refresh(pat)
        if db.query(Prescription).count()==0:
            db.add(Prescription(patient_id=pat.id,doctor_id=doc.id,medication_name="Demo medication A",dosage="As prescribed",
              schedule="Morning and evening",instructions="Fictional demonstration record",start_date=date.today().isoformat(),
              end_date=(date.today()+timedelta(days=7)).isoformat(),status="active")); db.commit()

@app.get("/")
def root(): return {"name":"MediSync API","status":"running","docs":"/docs"}
@app.get("/api/health")
def health(): return {"status":"ok","time":datetime.utcnow().isoformat()}
@app.post("/api/auth/login")
def login(x: LoginIn, db: Session=Depends(get_db)):
    u=db.query(User).filter_by(email=x.email.lower()).first()
    if not u or not pwd.verify(x.password,u.password_hash): raise HTTPException(401,"Incorrect email or password")
    return {"access_token":token_for(u),"token_type":"bearer","user":{"id":u.id,"name":u.name,"email":u.email,"role":u.role}}
@app.get("/api/auth/me")
def me(u: User=Depends(current_user)): return {"id":u.id,"name":u.name,"email":u.email,"role":u.role}
@app.get("/api/patients")
def patients(db: Session=Depends(get_db), u: User=Depends(role_required("doctor"))):
    return [{"id":p.id,"name":p.name,"email":p.email,"role":p.role} for p in db.query(User).filter_by(role="patient").all()]
@app.get("/api/prescriptions")
def prescriptions(db: Session=Depends(get_db), u: User=Depends(current_user)):
    q=db.query(Prescription)
    q=q.filter_by(patient_id=u.id) if u.role=="patient" else q.filter_by(doctor_id=u.id)
    return [serialize(p,db) for p in q.order_by(Prescription.id.desc()).all()]
@app.post("/api/prescriptions", status_code=201)
def create_prescription(x: PrescriptionIn, db: Session=Depends(get_db), u: User=Depends(role_required("doctor"))):
    patient=db.query(User).filter_by(email=x.patient_email.lower(),role="patient").first()
    if not patient: raise HTTPException(404,"Patient account not found")
    try:
        start,end=date.fromisoformat(x.start_date),date.fromisoformat(x.end_date)
        if end<start: raise ValueError()
    except ValueError: raise HTTPException(422,"Use valid YYYY-MM-DD dates; end date must not precede start date")
    p=Prescription(patient_id=patient.id,doctor_id=u.id,medication_name=x.medication_name.strip(),dosage=x.dosage.strip(),
      schedule=x.schedule.strip(),instructions=x.instructions.strip(),start_date=x.start_date,end_date=x.end_date,status="active")
    db.add(p); db.commit(); db.refresh(p); log(db,u,"prescription_created",f"Prescription #{p.id}")
    return serialize(p,db)
@app.patch("/api/prescriptions/{pid}")
def update_prescription(pid:int,x:StatusIn,db:Session=Depends(get_db),u:User=Depends(role_required("doctor"))):
    if x.status not in ("active","discontinued"): raise HTTPException(422,"Invalid status")
    p=db.get(Prescription,pid)
    if not p or p.doctor_id!=u.id: raise HTTPException(404,"Prescription not found")
    p.status=x.status; db.commit(); log(db,u,"prescription_"+x.status,f"Prescription #{pid}"); return serialize(p,db)
@app.get("/api/doses")
def doses(db:Session=Depends(get_db),u:User=Depends(current_user)):
    q=db.query(DoseLog)
    if u.role=="patient": q=q.filter_by(patient_id=u.id)
    else:
        ids=[p.id for p in db.query(Prescription).filter_by(doctor_id=u.id).all()]
        q=q.filter(DoseLog.prescription_id.in_(ids))
    return [{"id":d.id,"prescription_id":d.prescription_id,"patient_id":d.patient_id,"scheduled_for":d.scheduled_for,
      "status":d.status,"note":d.note,"recorded_at":d.recorded_at.isoformat()} for d in q.order_by(DoseLog.id.desc()).limit(100).all()]
@app.post("/api/prescriptions/{pid}/doses",status_code=201)
def record_dose(pid:int,x:DoseIn,db:Session=Depends(get_db),u:User=Depends(role_required("patient"))):
    if x.status not in ("taken","missed","skipped"): raise HTTPException(422,"Invalid dose status")
    p=db.get(Prescription,pid)
    if not p or p.patient_id!=u.id or p.status!="active": raise HTTPException(404,"Active prescription not found")
    d=DoseLog(prescription_id=p.id,patient_id=u.id,scheduled_for=x.scheduled_for,status=x.status,note=x.note[:300])
    db.add(d); db.commit(); db.refresh(d); log(db,u,"dose_recorded",f"Dose #{d.id}: {d.status}")
    return {"id":d.id,"prescription_id":d.prescription_id,"patient_id":d.patient_id,"scheduled_for":d.scheduled_for,"status":d.status,"note":d.note,"recorded_at":d.recorded_at.isoformat()}
@app.get("/api/alerts")
def alerts(db:Session=Depends(get_db),u:User=Depends(current_user)):
    q=db.query(Prescription).filter_by(status="active")
    q=q.filter_by(patient_id=u.id) if u.role=="patient" else q.filter_by(doctor_id=u.id)
    out=[]
    for p in q.all():
        if p.end_date<date.today().isoformat():
            out.append({"title":"Prescription end date passed","message":f"{p.medication_name}: confirm status with the prescribing clinician.","severity":"medium","prescription_id":p.id})
        missed=db.query(DoseLog).filter_by(prescription_id=p.id,status="missed").order_by(DoseLog.id.desc()).first()
        if missed: out.append({"title":"Missed dose recorded","message":f"{p.medication_name}: missed dose recorded for {missed.scheduled_for}. Follow clinician/pharmacist instructions; do not double a dose unless instructed.","severity":"medium","prescription_id":p.id})
    return out
@app.post("/api/safety/demo-check")
def safety(x:SafetyIn,u:User=Depends(current_user)):
    # Deliberately illustrative, not a clinical interaction dataset.
    names=[n.strip().lower() for n in x.medication_names if n.strip()]
    sample={"demo medication a","demo medication b"}
    found=any({names[i],names[j]}==sample for i in range(len(names)) for j in range(i+1,len(names)))
    warnings=[{"medications":["Demo medication A","Demo medication B"],"warning":"Illustrative sample rule only; not a real or validated clinical interaction finding."}] if found else []
    return {"mode":"DEMO_ONLY_NOT_CLINICALLY_VALIDATED","message":"This checker cannot determine medication safety. Ask a qualified clinician or pharmacist to review actual medications.","warnings":warnings}
@app.get("/api/audit")
def audit(db:Session=Depends(get_db),u:User=Depends(role_required("doctor"))):
    return [{"id":a.id,"actor_id":a.actor_id,"action":a.action,"details":a.details,"created_at":a.created_at.isoformat()} for a in db.query(AuditLog).order_by(AuditLog.id.desc()).limit(100).all()]
