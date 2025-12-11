# backend/agents/intake_agent.py
from fastapi import HTTPException
from backend.database import SessionLocal
from backend.models.db_models import Application
import datetime

# Utility to create application programmatically (if other code calls it)
def create_application_from_request(req):
    db = SessionLocal()
    try:
        dob = req.dob if isinstance(req.dob, datetime.date) else None
        if dob is None:
            raise ValueError("DOB not parsed to date")

        app = Application(
            name=req.name,
            dob=dob,
            phone=req.phone,
            email=req.email,
            aadhaar=req.aadhaar_number,
            pan=req.pan,
            address=req.address,
            income=req.income,
            loan_amount=req.loan_amount,
            loan_tenure=req.loan_tenure,
        )
        db.add(app)
        db.commit()
        db.refresh(app)
        return app.app_id

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create application: {e}")
    finally:
        db.close()
