from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Date,
    DateTime,
    Text,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()


# 1) Base application table
class Application(Base):
    __tablename__ = "applications"

    app_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    dob = Column(Date)
    phone = Column(String)
    email = Column(String)
    pan = Column(String)
    address = Column(Text)
    income = Column(Integer)
    loan_amount = Column(Integer)
    loan_tenure = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.now)
    status = Column(String, default="PENDING")


# 2) OCR output from documents (ID, etc.)
class KYCData(Base):
    __tablename__ = "kyc_data"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, index=True)
    extracted_name = Column(String)
    extracted_dob = Column(String)
    extracted_pan = Column(String)
    extracted_address = Column(Text)  # <── ADD THIS
    ocr_confidence = Column(Float)
    updated_at = Column(DateTime, default=datetime.datetime.now)



# 3) Final KYC check results (PAN+face)
class KYCResult(Base):
    __tablename__ = "kyc_results"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, index=True)
    pan_verified = Column(Boolean, default=False)
    face_match_score = Column(Float, default=0.0)
    kyc_status = Column(String, default="PENDING")
    updated_at = Column(DateTime, default=datetime.datetime.now)


# 4) Fraud checks (doc tampering etc.) – you’ll use later
class FraudChecks(Base):
    __tablename__ = "fraud_checks"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, index=True)
    fraud_score = Column(Float)
    blur_level = Column(Float)
    tamper_detected = Column(Boolean)
    fraud_status = Column(String)  # PASS / FAIL / MANUAL
    updated_at = Column(DateTime, default=datetime.datetime.now)


# 5) Credit scoring model output
class CreditScores(Base):
    __tablename__ = "credit_scores"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, index=True)
    model_score = Column(Float)
    approval_status = Column(String)  # APPROVED / REJECTED / MANUAL
    sanctioned_amount = Column(Integer)
    interest_rate = Column(Float)
    shap_top_features = Column(JSON)
    updated_at = Column(DateTime, default=datetime.datetime.now)


# 6) Final decision + explanation text
class Decisions(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, index=True)
    final_status = Column(String)  # APPROVED / REJECTED / MANUAL
    explanation = Column(Text)
    updated_at = Column(DateTime, default=datetime.datetime.now)


# 7) Manual review overrides
class ManualReview(Base):
    __tablename__ = "manual_review"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, index=True)
    reviewer = Column(String)
    decision = Column(String)  # APPROVE / REJECT
    notes = Column(Text)
    reviewed_at = Column(DateTime, default=datetime.datetime.now)
