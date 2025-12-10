from backend.database import SessionLocal
from backend.models.db_models import Application
from datetime import datetime

def create_application(data):
    db = SessionLocal()

    dob_obj = datetime.strptime(data.dob, "%Y-%m-%d").date()

    new_app = Application(
        name=data.name,
        dob=dob_obj,
        phone=data.phone,
        email=data.email,
        pan=data.pan,
        address=data.address,
        income=data.income,
        loan_amount=data.loan_amount,
        loan_tenure=data.loan_tenure,
        created_at=datetime.now(),
        status="PENDING"
    )

    db.add(new_app)
    db.commit()
    db.refresh(new_app)
    db.close()

    return new_app.app_id
