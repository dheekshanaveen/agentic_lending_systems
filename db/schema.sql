-- APPLICATION BASIC DETAILS
CREATE TABLE applications (
    app_id SERIAL PRIMARY KEY,
    name TEXT,
    dob DATE,
    phone TEXT,
    email TEXT,
    pan TEXT,
    address TEXT,
    income INTEGER,
    loan_amount INTEGER,
    loan_tenure INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'PENDING'
);

-- OCR EXTRACTED DATA
CREATE TABLE kyc_data (
    id SERIAL PRIMARY KEY,
    app_id INTEGER REFERENCES applications(app_id),
    extracted_name TEXT,
    extracted_dob TEXT,
    extracted_pan TEXT,
    ocr_confidence FLOAT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- FACE MATCH + LIVENESS + ID MATCH
CREATE TABLE kyc_checks (
    id SERIAL PRIMARY KEY,
    app_id INTEGER REFERENCES applications(app_id),
    face_match_score FLOAT,
    liveness_score FLOAT,
    name_match BOOLEAN,
    dob_match BOOLEAN,
    kyc_status TEXT,          -- PASS / FAIL / MANUAL
    updated_at TIMESTAMP DEFAULT NOW()
);

-- FRAUD DETECTION RESULTS
CREATE TABLE fraud_checks (
    id SERIAL PRIMARY KEY,
    app_id INTEGER REFERENCES applications(app_id),
    fraud_score FLOAT,
    blur_level FLOAT,
    tamper_detected BOOLEAN,
    fraud_status TEXT,         -- PASS / FAIL / MANUAL
    updated_at TIMESTAMP DEFAULT NOW()
);

-- CREDIT SCORING OUTPUT
CREATE TABLE credit_scores (
    id SERIAL PRIMARY KEY,
    app_id INTEGER REFERENCES applications(app_id),
    model_score FLOAT,
    approval_status TEXT,       -- APPROVED / REJECTED / MANUAL
    sanctioned_amount INTEGER,
    interest_rate FLOAT,
    shap_top_features JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- FINAL DECISION + EXPLANATION AGENT OUTPUT
CREATE TABLE decisions (
    id SERIAL PRIMARY KEY,
    app_id INTEGER REFERENCES applications(app_id),
    final_status TEXT,          -- APPROVED / REJECTED / MANUAL
    explanation TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- MANUAL REVIEW
CREATE TABLE manual_review (
    id SERIAL PRIMARY KEY,
    app_id INTEGER REFERENCES applications(app_id),
    reviewer TEXT,
    decision TEXT,              -- APPROVE / REJECT
    notes TEXT,
    reviewed_at TIMESTAMP DEFAULT NOW()
);
