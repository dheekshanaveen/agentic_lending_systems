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
    
    # --- add these below existing classes in backend/models/db_models.py ---


class SalarySlip(Base):
    __tablename__ = "salary_slips"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, index=True)
    file_path = Column(String, nullable=True)
    employer = Column(String, nullable=True)
    employee_name = Column(String, nullable=True)
    employee_id = Column(String, nullable=True)
    month = Column(String, nullable=True)
    gross_amount = Column(Float, nullable=True)
    net_amount = Column(Float, nullable=True)
    parsed_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)


class BankStatement(Base):
    __tablename__ = "bank_statements"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, index=True)
    file_path = Column(String, nullable=True)
    account_holder = Column(String, nullable=True)
    account_number = Column(String, nullable=True)
    avg_balance = Column(Float, nullable=True)
    total_inflow = Column(Float, nullable=True)
    parsed_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)


class IncomeVerification(Base):
    __tablename__ = "income_verifications"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, index=True)
    status = Column(String)  # APPROVED / REJECTED / MANUAL
    reason = Column(Text, nullable=True)
    extracted_name = Column(String, nullable=True)
    extracted_employee_id = Column(String, nullable=True)
    extracted_salary = Column(Float, nullable=True)
    saved_payload = Column(Text, nullable=True)  # JSON of results
    created_at = Column(DateTime, default=datetime.datetime.now)
