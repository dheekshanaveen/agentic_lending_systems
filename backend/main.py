from fastapi import FastAPI

from backend.routers import intake, ocr, kyc
from backend.models.db_models import Base
from backend.database import engine
from backend.routers import intake, ocr, kyc, aadhar
app = FastAPI(title="Agentic Lending System")

# create tables
Base.metadata.create_all(bind=engine)

# routers
app.include_router(intake.router)
app.include_router(ocr.router)
app.include_router(kyc.router)
app.include_router(aadhar.router)

@app.get("/")
def root():
    return {"message": "Agentic Lending API is running"}
