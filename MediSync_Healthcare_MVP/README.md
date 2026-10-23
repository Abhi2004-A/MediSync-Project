# MediSync — Doctor–Medication Coordination MVP

Stack: React + JavaScript + Vite, Python FastAPI, SQLite, Docker.

## Backend
Python 3.10+:
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

Demo logins:
- Doctor: doctor@medisync.demo / Doctor123!
- Patient: patient@medisync.demo / Patient123!

## Frontend
In another terminal:
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. Backend API defaults to http://127.0.0.1:8000/api.
To override, create `frontend/.env` from `.env.example`.

## Demo flow
1. Sign in as doctor and create a prescription for `patient@medisync.demo`.
2. Sign out, sign in as patient and view medication records.
3. Record a dose as taken or missed and view alerts.
4. Try the demo safety checker using `Demo medication A, Demo medication B`.

## Safety / security
This is a hackathon prototype, not a clinical decision-support system. The interaction rule is illustrative and not medically validated. Do not use real patient data or use this checker for treatment decisions. Production use requires validated clinical data, professional review, security/privacy assessment, strong secrets, HTTPS, database migrations/backups and jurisdiction-specific compliance review. Change demo credentials and JWT secret before any deployment.
