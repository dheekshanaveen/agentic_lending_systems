# backend/schemas/request_schemas.py
from pydantic import BaseModel, validator
from typing import Optional
import datetime
import re

DATE_FORMATS = [
    "%Y-%m-%d",  # 2006-12-11
    "%d-%m-%Y",  # 11-12-2006
    "%d/%m/%Y",  # 11/12/2006
    "%Y/%m/%d",  # 2006/12/11
]

def normalize_date_string(s: str) -> str:
    # Replace common separators with hyphen for consistent parsing
    return re.sub(r"[\/\s\.]", "-", s.strip())

class ApplicationRequest(BaseModel):
    name: str
    dob: datetime.date      # pydantic will hold a date object after validator
    phone: str
    email: str
    aadhaar_number: str
    pan: Optional[str] = None
    address: str
    income: int
    loan_amount: int
    loan_tenure: int

    # Accept several common formats and normalize to datetime.date
    @validator("dob", pre=True)
    def convert_dob(cls, v):
        # If already a date (pydantic may parse), return it
        if isinstance(v, datetime.date):
            return v

        if not isinstance(v, str):
            raise ValueError("DOB must be a string in YYYY-MM-DD or DD-MM-YYYY format")

        s = normalize_date_string(v)
        for fmt in DATE_FORMATS:
            try:
                return datetime.datetime.strptime(s, fmt).date()
            except Exception:
                continue

        # explicit, clear error so client sees what's wrong
        raise ValueError("DOB must be in one of: YYYY-MM-DD, DD-MM-YYYY, or DD/MM/YYYY")
