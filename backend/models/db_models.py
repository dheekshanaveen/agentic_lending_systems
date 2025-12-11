# backend/models/db_models.py
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Text
)
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class Application(Base):
    __tablename__ = "applications"

    app_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    dob = Column(Date)
    phone = Column(String)
    email = Column(String)
    aadhaar = Column(String)
    pan = Column(String)
    address = Column(Text)
    income = Column(Integer)
    loan_amount = Column(Integer)
    loan_tenure = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.now)
    status = Column(String, default="PENDING")


# 2) OCR output
class KYCData(Base):
    __tablename__ = "kyc_data"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, index=True)

    extracted_name = Column(String)
    extracted_dob = Column(String)
    extracted_aadhaar = Column(String)
    extracted_pan = Column(String)        # NEW
    extracted_address = Column(Text)

    ocr_confidence = Column(Float)
    updated_at = Column(DateTime, default=datetime.datetime.now)


class KYCResult(Base):
    __tablename__ = "kyc_results"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, index=True)
    kyc_status = Column(String)
    failed_fields = Column(Text)
    updated_at = Column(DateTime, default=datetime.datetime.now)
