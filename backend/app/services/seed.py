import json

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import (
    ClinicalAnswer,
    ClinicalCase,
    ClinicalNote,
    ClinicalQuestion,
    PatientAssignment,
    ReviewerFeedback,
    User,
)

DEMO_DOCTOR_EMAILS = {
    "maya.chen@docpilot.health",
    "sahith@docpilot.health",
    "vijay@docpilot.health",
    "ashish@docpilot.health",
}


def seed_demo_data(db: Session) -> None:
    reset_chat_history(db)
    doctors = _upsert_demo_doctors(db)
    cases = _demo_cases()
    case_ids = [case["id"] for case in cases]

    if case_ids:
        db.query(ClinicalNote).filter(ClinicalNote.case_id.in_(case_ids)).delete(
            synchronize_session=False
        )

    for case_payload in cases:
        clinical_case = db.get(ClinicalCase, case_payload["id"])
        if clinical_case is None:
            clinical_case = ClinicalCase(id=case_payload["id"])
            db.add(clinical_case)

        clinical_case.patient_name = case_payload["patient_name"]
        clinical_case.mrn = case_payload["mrn"]
        clinical_case.age = case_payload["age"]
        clinical_case.sex = case_payload["sex"]
        clinical_case.primary_concern = case_payload["primary_concern"]
        clinical_case.risk_level = case_payload["risk_level"]
        clinical_case.status = case_payload["status"]
        clinical_case.admitted_at = case_payload["admitted_at"]
        clinical_case.timeline_json = json.dumps(case_payload["timeline"])
        clinical_case.active_problems_json = json.dumps(case_payload["active_problems"])
        clinical_case.medications_json = json.dumps(case_payload["medications"])
        clinical_case.labs_json = json.dumps(case_payload["labs"])
        clinical_case.vitals_json = json.dumps(case_payload["vitals"])
        clinical_case.suggested_questions_json = json.dumps(case_payload["suggested_questions"])

        for note_payload in case_payload["notes"]:
            db.add(ClinicalNote(case_id=case_payload["id"], **note_payload))

    db.flush()
    _assign_seed_patients(db, doctors)
    db.flush()


def reset_chat_history(db: Session) -> dict[str, int]:
    feedback_count = db.query(ReviewerFeedback).delete(synchronize_session=False)
    answer_count = db.query(ClinicalAnswer).delete(synchronize_session=False)
    question_count = db.query(ClinicalQuestion).delete(synchronize_session=False)
    return {
        "feedback": feedback_count,
        "answers": answer_count,
        "questions": question_count,
    }


def assign_all_cases_to_doctor(db: Session, doctor_id: str) -> None:
    for case_id, in db.query(ClinicalCase.id).all():
        _assign_case(db, doctor_id, case_id)


def _upsert_demo_doctors(db: Session) -> dict[str, User]:
    doctors = [
        {
            "email": "maya.chen@docpilot.health",
            "full_name": "Dr. Maya Chen",
            "role": "physician",
            "specialty": "Internal Medicine",
            "password": "demo-clinical",
        },
        {
            "email": "sahith@docpilot.health",
            "full_name": "Dr. Sahith Reddy",
            "role": "physician",
            "specialty": "Hospital Medicine",
            "password": "demo-clinical",
        },
        {
            "email": "vijay@docpilot.health",
            "full_name": "Dr. Vijay Rao",
            "role": "physician",
            "specialty": "Cardiology",
            "password": "demo-clinical",
        },
        {
            "email": "ashish@docpilot.health",
            "full_name": "Dr. Ashish Patel",
            "role": "physician",
            "specialty": "Endocrinology",
            "password": "demo-clinical",
        },
    ]
    records: dict[str, User] = {}
    for payload in doctors:
        doctor = db.query(User).filter(User.email == payload["email"]).first()
        if doctor is None:
            doctor = User(
                email=payload["email"],
                full_name=payload["full_name"],
                role=payload["role"],
                specialty=payload["specialty"],
                password_hash=hash_password(payload["password"]),
            )
            db.add(doctor)
            db.flush()
        else:
            doctor.full_name = payload["full_name"]
            doctor.role = payload["role"]
            doctor.specialty = payload["specialty"]
        records[doctor.email] = doctor
    return records


def _assign_seed_patients(db: Session, doctors: dict[str, User]) -> None:
    seed_doctor_ids = [doctor.id for doctor in doctors.values()]
    if seed_doctor_ids:
        db.query(PatientAssignment).filter(PatientAssignment.doctor_id.in_(seed_doctor_ids)).delete(
            synchronize_session=False
        )

    assignment_map = {
        "maya.chen@docpilot.health": [
            "case-singh-003",
            "case-ibarra-002",
            "case-marlowe-001",
        ],
        "sahith@docpilot.health": [
            "case-lee-006",
            "case-ramirez-007",
            "case-kim-010",
        ],
        "vijay@docpilot.health": [
            "case-hayes-004",
            "case-brooks-008",
            "case-park-012",
        ],
        "ashish@docpilot.health": [
            "case-patel-005",
            "case-yusuf-009",
            "case-hassan-011",
        ],
    }
    for email, case_ids in assignment_map.items():
        for case_id in case_ids:
            _assign_case(db, doctors[email].id, case_id)


def _assign_case(db: Session, doctor_id: str, case_id: str) -> None:
    existing = (
        db.query(PatientAssignment)
        .filter(PatientAssignment.doctor_id == doctor_id, PatientAssignment.case_id == case_id)
        .first()
    )
    if existing is None:
        db.add(PatientAssignment(doctor_id=doctor_id, case_id=case_id))


def _demo_cases() -> list[dict[str, object]]:
    return [
        _case(
            key="singh",
            case_id="case-singh-003",
            patient_name="Priya Singh",
            mrn="SYN-10103",
            age=66,
            sex="female",
            primary_concern="syncope after antihypertensive medication change",
            risk_level="stable",
            status="review",
            admitted_at="2026-05-19T16:40:00Z",
            active_problems=[
                "Orthostatic syncope",
                "Recent lisinopril-hydrochlorothiazide dose increase",
                "Volume depletion risk",
                "Arrhythmia less supported by telemetry",
            ],
            medications=[
                {"name": "Lisinopril-hydrochlorothiazide", "dose": "recently increased", "status": "hold and reassess"},
                {"name": "Amlodipine", "dose": "5 mg daily", "status": "continue if seated BP allows"},
                {"name": "Oral fluids", "dose": "encourage intake", "status": "active"},
                {"name": "Compression stockings", "dose": "during ambulation", "status": "recommended"},
            ],
            labs=[
                {"name": "Troponin", "value": "negative x2", "flag": "reassuring"},
                {"name": "Creatinine", "value": "1.2 mg/dL", "flag": "near baseline"},
                {"name": "Sodium", "value": "134 mmol/L", "flag": "mildly low"},
            ],
            vitals=[
                {"name": "Orthostatic BP", "value": "142/76 seated -> 104/62 standing", "flag": "abnormal"},
                {"name": "Telemetry", "value": "sinus rhythm, rare PACs", "flag": "no sustained arrhythmia"},
            ],
            timeline=[
                {"date": "2026-05-18", "label": "Medication change", "detail": "Home antihypertensive dose was increased after elevated clinic readings."},
                {"date": "2026-05-19", "label": "Standing event", "detail": "Brief syncope occurred while standing in the kitchen."},
                {"date": "2026-05-19", "label": "ED evaluation", "detail": "Orthostatic vitals were positive and CT head was negative."},
                {"date": "2026-05-20", "label": "Telemetry review", "detail": "No high-grade block, pauses, or sustained tachyarrhythmia captured."},
                {"date": "2026-05-20", "label": "Discharge review", "detail": "Medication reconciliation and fall precautions were prioritized."},
            ],
            suggested_questions=[
                "Why is orthostatic hypotension favored over arrhythmia for syncope?",
                "What medication change matters most in this case?",
                "What findings argue against an arrhythmia-driven event?",
                "What should be reviewed before discharge?",
            ],
            notes=[
                ("admission_note", "resident physician", "2026-05-19", "Syncope Admission HPI", "Patient had a brief syncopal episode while standing in the kitchen one day after lisinopril-hydrochlorothiazide was increased. Orthostatic vitals are positive in the emergency department. She reports lightheadedness when standing but no chest pain, palpitations, focal neurologic deficit, or seizure-like activity."),
                ("ed_note", "emergency physician", "2026-05-19", "Initial ED Evaluation", "CT head shows no acute findings. ECG shows sinus rhythm without ischemic ST changes. Troponin is negative twice. Blood pressure falls from 142/76 seated to 104/62 standing with symptoms, supporting orthostatic hypotension in this synthetic case."),
                ("telemetry_note", "cardiology fellow", "2026-05-20", "Telemetry Review", "Telemetry overnight shows sinus rhythm with rare premature atrial contractions. No high-grade AV block, sustained tachyarrhythmia, or pauses were captured. The available evidence favors orthostatic syncope after medication change rather than arrhythmia."),
                ("progress_note", "attending physician", "2026-05-20", "Discharge Safety Review", "Plan is to hold the diuretic component temporarily, review home blood pressure logs, encourage hydration, and assess gait before discharge. Patient education focuses on slow position changes and follow-up medication titration."),
            ],
        ),
        _case(
            key="ibarra",
            case_id="case-ibarra-002",
            patient_name="Jon Ibarra",
            mrn="SYN-10077",
            age=58,
            sex="male",
            primary_concern="diabetic foot infection with hyperglycemia",
            risk_level="watch",
            status="active",
            admitted_at="2026-05-02T11:30:00Z",
            active_problems=[
                "Diabetic foot infection",
                "Left plantar cellulitis",
                "Poor glycemic control",
                "Insulin adherence barriers",
            ],
            medications=[
                {"name": "Vancomycin", "dose": "pharmacy dosed", "status": "empiric"},
                {"name": "Cefepime", "dose": "2 g every 8 hours", "status": "empiric"},
                {"name": "Glargine", "dose": "22 units nightly", "status": "active"},
                {"name": "Lispro", "dose": "correctional with meals", "status": "active"},
            ],
            labs=[
                {"name": "WBC", "value": "15.8 K/uL", "flag": "high"},
                {"name": "Lactate", "value": "1.7 mmol/L", "flag": "normal"},
                {"name": "A1c", "value": "10.2%", "flag": "high"},
            ],
            vitals=[
                {"name": "Temperature", "value": "100.6 F", "flag": "febrile"},
                {"name": "Glucose", "value": "260-340 mg/dL", "flag": "high"},
            ],
            timeline=[
                {"date": "2026-05-02", "label": "Foot wound intake", "detail": "Left plantar ulcer with warmth, swelling, and drainage."},
                {"date": "2026-05-02", "label": "Initial labs", "detail": "WBC elevated, lactate normal, glucose persistently high."},
                {"date": "2026-05-02", "label": "Empiric antibiotics", "detail": "Vancomycin plus cefepime started pending cultures."},
                {"date": "2026-05-03", "label": "MRI review", "detail": "Cellulitis without abscess or osteomyelitis."},
                {"date": "2026-05-03", "label": "Diabetes plan", "detail": "Basal insulin and education aligned with night-shift schedule."},
            ],
            suggested_questions=[
                "What evidence supports diabetic foot infection severity?",
                "What glucose trends matter for inpatient management?",
                "What antibiotics or wound findings are relevant?",
                "What discharge risks should be reviewed?",
            ],
            notes=[
                ("ed_note", "emergency physician", "2026-05-02", "Foot Wound Intake", "Patient with type 2 diabetes presents with three days of left plantar redness, warmth, swelling, and drainage from a shallow ulcer below the first metatarsal head. Temperature is 100.6 F and heart rate is 104. No crepitus is felt."),
                ("lab_review", "hospitalist", "2026-05-02", "Admission Infection Review", "White blood cell count is 15.8 K/uL and lactate is 1.7 mmol/L. Plain film shows soft tissue swelling without gas. The pattern supports diabetic foot infection with cellulitis but not necrotizing infection."),
                ("imaging_report", "radiology", "2026-05-03", "Left Foot MRI", "MRI left foot shows plantar soft tissue ulceration and cellulitis near the first metatarsal head. There is no marrow replacement, cortical destruction, or abscess. Findings do not support osteomyelitis."),
                ("consult_note", "endocrinology", "2026-05-03", "Glucose Management", "A1c is 10.2 percent and glucose values range from 260 to 340 mg/dL. Patient reports missed basal insulin several times per week because of night-shift schedule changes. Recommend glargine, correctional lispro, and diabetes education."),
            ],
        ),
        _case(
            key="marlowe",
            case_id="case-marlowe-001",
            patient_name="Elaine Marlowe",
            mrn="SYN-10042",
            age=72,
            sex="female",
            primary_concern="progressive dyspnea, edema, and hypoxemia",
            risk_level="high",
            status="active",
            admitted_at="2026-04-18T08:15:00Z",
            active_problems=[
                "Acute decompensated heart failure",
                "Hypoxemia",
                "Mild kidney injury",
                "Hyponatremia during diuresis",
            ],
            medications=[
                {"name": "Furosemide", "dose": "40 mg IV twice daily", "status": "active"},
                {"name": "Carvedilol", "dose": "6.25 mg twice daily", "status": "continue"},
                {"name": "Potassium chloride", "dose": "as needed", "status": "replete"},
                {"name": "Magnesium oxide", "dose": "as needed", "status": "replete"},
            ],
            labs=[
                {"name": "BNP", "value": "1420 pg/mL", "flag": "high"},
                {"name": "Creatinine", "value": "1.5 mg/dL", "flag": "above baseline"},
                {"name": "Troponin", "value": "18 -> 19 ng/L", "flag": "flat"},
            ],
            vitals=[
                {"name": "Oxygen saturation", "value": "88% room air -> 95% on 1 L", "flag": "improving"},
                {"name": "Volume status", "value": "JVP elevated, 2+ edema", "flag": "overloaded"},
            ],
            timeline=[
                {"date": "2026-04-18", "label": "ED arrival", "detail": "Dyspnea, orthopnea, edema, and hypoxemia."},
                {"date": "2026-04-18", "label": "Imaging", "detail": "Chest x-ray showed vascular congestion and small effusions."},
                {"date": "2026-04-18", "label": "Lab review", "detail": "BNP 1420 with flat troponin trend."},
                {"date": "2026-04-19", "label": "Diuresis", "detail": "IV furosemide started with strict intake and output."},
                {"date": "2026-04-19", "label": "Response", "detail": "Oxygen requirement and orthopnea improved after diuresis."},
            ],
            suggested_questions=[
                "What evidence supports heart failure as the main driver of dyspnea?",
                "What findings increase concern for volume overload?",
                "What oxygen or imaging findings matter most?",
                "What should be monitored after diuresis?",
            ],
            notes=[
                ("ed_note", "emergency physician", "2026-04-18", "Emergency Department Assessment", "Patient reports four days of progressive dyspnea, orthopnea, and bilateral leg swelling. Oxygen saturation was 88 percent on room air and improved to 94 percent on 2 L nasal cannula. Exam shows bibasilar crackles, elevated jugular venous pressure, and 2+ pitting edema."),
                ("imaging_report", "radiology", "2026-04-18", "Chest X-ray", "Chest x-ray describes pulmonary vascular congestion with small bilateral pleural effusions. No focal lobar consolidation was described. The imaging supports volume overload in this synthetic case."),
                ("lab_review", "hospitalist", "2026-04-18", "Admission Lab Review", "BNP is elevated at 1420 pg/mL. Creatinine is 1.5 mg/dL compared with baseline near 1.1. Troponin is 18 then 19 with no dynamic rise and procalcitonin is low at 0.04."),
                ("progress_note", "attending physician", "2026-04-19", "Hospital Day 1 Plan", "Assessment favors acute decompensated heart failure as the main driver of dyspnea given orthopnea, edema, crackles, vascular congestion, and BNP 1420. Plan is IV furosemide, daily weights, electrolyte repletion, and renal monitoring."),
            ],
        ),
        _case(
            key="hayes",
            case_id="case-hayes-004",
            patient_name="Robert Hayes",
            mrn="SYN-10144",
            age=64,
            sex="male",
            primary_concern="chest pain with elevated troponin trend",
            risk_level="high",
            status="active",
            admitted_at="2026-05-22T09:05:00Z",
            active_problems=["NSTEMI concern", "Hypertension", "Hyperlipidemia", "Contrast kidney risk"],
            medications=[
                {"name": "Aspirin", "dose": "81 mg daily", "status": "active"},
                {"name": "Heparin infusion", "dose": "ACS protocol", "status": "active"},
                {"name": "Atorvastatin", "dose": "80 mg nightly", "status": "active"},
                {"name": "Metoprolol tartrate", "dose": "12.5 mg twice daily", "status": "active"},
            ],
            labs=[
                {"name": "Troponin", "value": "42 -> 118 -> 176 ng/L", "flag": "rising"},
                {"name": "Creatinine", "value": "1.3 mg/dL", "flag": "watch"},
                {"name": "LDL", "value": "146 mg/dL", "flag": "high"},
            ],
            vitals=[
                {"name": "Blood pressure", "value": "162/88", "flag": "elevated"},
                {"name": "ECG", "value": "lateral ST depressions", "flag": "ischemic concern"},
            ],
            timeline=[
                {"date": "2026-05-22", "label": "Chest pain onset", "detail": "Pressure-like pain radiated to left arm during exertion."},
                {"date": "2026-05-22", "label": "ECG", "detail": "Lateral ST depressions without ST elevation."},
                {"date": "2026-05-22", "label": "Troponin trend", "detail": "Serial troponin rose from 42 to 176."},
                {"date": "2026-05-22", "label": "ACS therapy", "detail": "Aspirin, heparin, beta blocker, and high-intensity statin started."},
                {"date": "2026-05-23", "label": "Cath planning", "detail": "Cardiology planned angiography with renal protection."},
            ],
            suggested_questions=[
                "What evidence supports NSTEMI rather than non-cardiac chest pain?",
                "How should the troponin trend be interpreted?",
                "What therapies were started for ACS risk?",
                "What kidney risk matters before angiography?",
            ],
            notes=[
                ("ed_note", "emergency physician", "2026-05-22", "Chest Pain Intake", "Patient reports pressure-like chest pain radiating to the left arm while climbing stairs. Pain improved with nitroglycerin. ECG shows lateral ST depressions without ST elevation."),
                ("lab_review", "hospitalist", "2026-05-22", "Troponin Trend", "High sensitivity troponin increased from 42 to 118 to 176 ng/L over serial checks. The rising pattern supports acute myocardial injury in the setting of ischemic symptoms."),
                ("consult_note", "cardiology", "2026-05-22", "Cardiology Assessment", "Assessment is NSTEMI concern. Recommend aspirin, heparin infusion, high-intensity statin, beta blocker if tolerated, telemetry, and coronary angiography when renal status is acceptable."),
                ("progress_note", "attending physician", "2026-05-23", "Pre-Cath Review", "Creatinine is 1.3 mg/dL and baseline is unknown. Plan includes avoiding nephrotoxins, using contrast sparingly, and trending renal function after angiography."),
            ],
        ),
        _case(
            key="patel",
            case_id="case-patel-005",
            patient_name="Nisha Patel",
            mrn="SYN-10158",
            age=49,
            sex="female",
            primary_concern="uncontrolled type 2 diabetes with AKI risk",
            risk_level="watch",
            status="active",
            admitted_at="2026-05-24T13:20:00Z",
            active_problems=["Severe hyperglycemia", "Acute kidney injury risk", "Medication reconciliation", "Dehydration"],
            medications=[
                {"name": "Glargine", "dose": "18 units nightly", "status": "active"},
                {"name": "Lispro", "dose": "6 units with meals", "status": "active"},
                {"name": "Metformin", "dose": "hold", "status": "AKI risk"},
                {"name": "IV lactated Ringer's", "dose": "gentle hydration", "status": "active"},
            ],
            labs=[
                {"name": "Glucose", "value": "386 mg/dL", "flag": "high"},
                {"name": "A1c", "value": "11.4%", "flag": "high"},
                {"name": "Creatinine", "value": "1.8 mg/dL", "flag": "above baseline"},
            ],
            vitals=[
                {"name": "Heart rate", "value": "108", "flag": "tachycardic"},
                {"name": "Ketones", "value": "trace", "flag": "no DKA pattern"},
            ],
            timeline=[
                {"date": "2026-05-24", "label": "Clinic referral", "detail": "Sent to ED for glucose near 400 and reduced oral intake."},
                {"date": "2026-05-24", "label": "Renal concern", "detail": "Creatinine increased from baseline 1.0 to 1.8."},
                {"date": "2026-05-24", "label": "DKA screen", "detail": "Trace ketones and normal anion gap made DKA less likely."},
                {"date": "2026-05-25", "label": "Insulin plan", "detail": "Basal-bolus insulin started with diabetes education."},
                {"date": "2026-05-25", "label": "Medication hold", "detail": "Metformin held until renal function improves."},
            ],
            suggested_questions=[
                "What evidence supports AKI risk in this diabetes admission?",
                "Why is DKA less supported by the available data?",
                "What medication should be held while creatinine is elevated?",
                "What diabetes education issues should be addressed?",
            ],
            notes=[
                ("ed_note", "emergency physician", "2026-05-24", "Hyperglycemia Intake", "Patient presents after clinic glucose was near 400 mg/dL with several days of thirst and reduced oral intake. Heart rate is 108 and mucous membranes are dry."),
                ("lab_review", "hospitalist", "2026-05-24", "Diabetes And Kidney Labs", "Glucose is 386 mg/dL and A1c is 11.4 percent. Creatinine is 1.8 mg/dL compared with baseline 1.0. Anion gap is normal and serum ketones are trace, making DKA less supported."),
                ("pharmacy_note", "clinical pharmacist", "2026-05-24", "Medication Reconciliation", "Home metformin should be held while creatinine remains elevated. Recommend avoiding NSAIDs and checking renal function before restarting renally cleared diabetes medications."),
                ("consult_note", "diabetes educator", "2026-05-25", "Insulin Teaching", "Patient has been rationing test strips and skipping glucose checks at work. Education focused on basal insulin timing, correction scale use, hydration, and follow-up access to supplies."),
            ],
        ),
        _case(
            key="lee",
            case_id="case-lee-006",
            patient_name="Marcus Lee",
            mrn="SYN-10173",
            age=69,
            sex="male",
            primary_concern="COPD exacerbation with oxygen requirement",
            risk_level="watch",
            status="active",
            admitted_at="2026-05-25T07:45:00Z",
            active_problems=["COPD exacerbation", "Acute hypoxemia", "Steroid-related hyperglycemia", "Tobacco exposure"],
            medications=[
                {"name": "Prednisone", "dose": "40 mg daily", "status": "active"},
                {"name": "Ipratropium-albuterol", "dose": "nebulized every 4 hours", "status": "active"},
                {"name": "Azithromycin", "dose": "500 mg then 250 mg daily", "status": "active"},
                {"name": "Nicotine patch", "dose": "21 mg daily", "status": "active"},
            ],
            labs=[
                {"name": "VBG pCO2", "value": "58 mmHg", "flag": "elevated"},
                {"name": "WBC", "value": "11.9 K/uL", "flag": "mild high"},
                {"name": "Glucose", "value": "212 mg/dL", "flag": "steroid watch"},
            ],
            vitals=[
                {"name": "Oxygen saturation", "value": "86% room air -> 92% on 2 L", "flag": "improving"},
                {"name": "Respiratory rate", "value": "24", "flag": "elevated"},
            ],
            timeline=[
                {"date": "2026-05-25", "label": "ED arrival", "detail": "Wheezing, cough, and increased sputum with room air hypoxemia."},
                {"date": "2026-05-25", "label": "Gas review", "detail": "VBG showed chronic hypercapnia without severe acidosis."},
                {"date": "2026-05-25", "label": "Treatment", "detail": "Steroids, bronchodilators, and azithromycin started."},
                {"date": "2026-05-26", "label": "Oxygen walk", "detail": "Desaturated with ambulation, continued oxygen requirement."},
                {"date": "2026-05-26", "label": "Discharge planning", "detail": "Inhaler technique and smoking cessation reviewed."},
            ],
            suggested_questions=[
                "What evidence supports COPD exacerbation?",
                "What oxygen findings matter for discharge readiness?",
                "How should steroid-related glucose be monitored?",
                "What inhaler or tobacco counseling is documented?",
            ],
            notes=[
                ("ed_note", "emergency physician", "2026-05-25", "COPD Intake", "Patient presents with wheezing, increased cough, and thicker sputum. Oxygen saturation is 86 percent on room air and improves to 92 percent on 2 L nasal cannula."),
                ("lab_review", "hospitalist", "2026-05-25", "Gas And Lab Review", "VBG shows pH 7.34 and pCO2 58, consistent with chronic hypercapnia without severe acute acidosis. WBC is 11.9 K/uL and chest x-ray has no focal infiltrate."),
                ("progress_note", "attending physician", "2026-05-25", "Exacerbation Plan", "Plan is prednisone 40 mg daily, scheduled ipratropium-albuterol nebulizers, azithromycin, oxygen wean, and monitoring for steroid-related hyperglycemia."),
                ("respiratory_note", "respiratory therapist", "2026-05-26", "Ambulation And Education", "Patient desaturated to 88 percent during hallway ambulation on room air. Respiratory therapy reviewed inhaler technique, spacer use, and tobacco cessation resources."),
            ],
        ),
        _case(
            key="ramirez",
            case_id="case-ramirez-007",
            patient_name="Sofia Ramirez",
            mrn="SYN-10188",
            age=54,
            sex="female",
            primary_concern="pneumonia with sepsis monitoring",
            risk_level="high",
            status="active",
            admitted_at="2026-05-25T21:10:00Z",
            active_problems=["Community-acquired pneumonia", "Sepsis monitoring", "Hypoxemia", "Lactate clearance"],
            medications=[
                {"name": "Ceftriaxone", "dose": "1 g IV daily", "status": "active"},
                {"name": "Azithromycin", "dose": "500 mg daily", "status": "active"},
                {"name": "Acetaminophen", "dose": "650 mg as needed", "status": "active"},
                {"name": "Enoxaparin", "dose": "prophylaxis", "status": "active"},
            ],
            labs=[
                {"name": "WBC", "value": "18.4 K/uL", "flag": "high"},
                {"name": "Lactate", "value": "2.6 -> 1.4 mmol/L", "flag": "improving"},
                {"name": "Procalcitonin", "value": "1.8 ng/mL", "flag": "high"},
            ],
            vitals=[
                {"name": "Temperature", "value": "102.1 F -> 99.4 F", "flag": "improving"},
                {"name": "Oxygen saturation", "value": "89% room air -> 94% on 2 L", "flag": "improving"},
            ],
            timeline=[
                {"date": "2026-05-25", "label": "ED arrival", "detail": "Fever, productive cough, tachycardia, and hypoxemia."},
                {"date": "2026-05-25", "label": "Imaging", "detail": "Chest x-ray showed right lower lobe infiltrate."},
                {"date": "2026-05-25", "label": "Sepsis bundle", "detail": "Cultures, fluids, lactate check, and antibiotics completed."},
                {"date": "2026-05-26", "label": "Lactate response", "detail": "Lactate cleared from 2.6 to 1.4."},
                {"date": "2026-05-26", "label": "Oxygen wean", "detail": "Oxygen requirement improved but persisted with exertion."},
            ],
            suggested_questions=[
                "What evidence supports pneumonia with sepsis monitoring?",
                "How did the lactate trend change after treatment?",
                "What antibiotic plan is documented?",
                "What findings matter before oxygen weaning?",
            ],
            notes=[
                ("ed_note", "emergency physician", "2026-05-25", "Pneumonia Intake", "Patient presents with fever, productive cough, pleuritic discomfort, heart rate 118, and oxygen saturation 89 percent on room air. Chest x-ray shows a right lower lobe infiltrate."),
                ("lab_review", "hospitalist", "2026-05-25", "Sepsis Labs", "WBC is 18.4 K/uL, lactate is 2.6 mmol/L, and procalcitonin is 1.8 ng/mL. Blood cultures were collected before antibiotics."),
                ("progress_note", "attending physician", "2026-05-26", "Treatment Response", "Ceftriaxone and azithromycin continued for community-acquired pneumonia. Repeat lactate improved to 1.4 and temperature decreased after fluids and antibiotics."),
                ("nursing_note", "registered nurse", "2026-05-26", "Oxygen Monitoring", "Patient remains comfortable on 2 L nasal cannula with saturation 94 percent. She drops to 90 percent when walking to the bathroom and recovers with rest."),
            ],
        ),
        _case(
            key="brooks",
            case_id="case-brooks-008",
            patient_name="Daniel Brooks",
            mrn="SYN-10201",
            age=77,
            sex="male",
            primary_concern="anticoagulation review after atrial fibrillation admission",
            risk_level="watch",
            status="review",
            admitted_at="2026-05-26T10:25:00Z",
            active_problems=["Atrial fibrillation with rapid ventricular response", "Anticoagulation decision", "Fall risk review", "Renal dose review"],
            medications=[
                {"name": "Apixaban", "dose": "5 mg twice daily", "status": "planned"},
                {"name": "Metoprolol succinate", "dose": "50 mg daily", "status": "active"},
                {"name": "Diltiazem", "dose": "IV stopped", "status": "transitioned"},
                {"name": "Pantoprazole", "dose": "40 mg daily", "status": "active"},
            ],
            labs=[
                {"name": "Creatinine", "value": "1.2 mg/dL", "flag": "dose acceptable"},
                {"name": "Hemoglobin", "value": "12.6 g/dL", "flag": "stable"},
                {"name": "TSH", "value": "2.1", "flag": "normal"},
            ],
            vitals=[
                {"name": "Heart rate", "value": "138 -> 84", "flag": "controlled"},
                {"name": "CHA2DS2-VASc", "value": "4", "flag": "stroke risk"},
            ],
            timeline=[
                {"date": "2026-05-26", "label": "AF admission", "detail": "Presented with palpitations and rapid ventricular response."},
                {"date": "2026-05-26", "label": "Rate control", "detail": "Diltiazem drip transitioned to oral beta blocker."},
                {"date": "2026-05-26", "label": "Stroke risk", "detail": "CHA2DS2-VASc documented as 4."},
                {"date": "2026-05-27", "label": "Bleeding review", "detail": "No active bleeding and hemoglobin stable."},
                {"date": "2026-05-27", "label": "Discharge plan", "detail": "Apixaban education and fall risk counseling planned."},
            ],
            suggested_questions=[
                "What evidence supports starting anticoagulation?",
                "What bleeding or fall risks should be reviewed?",
                "How was rate control achieved?",
                "What renal dosing details matter for apixaban?",
            ],
            notes=[
                ("ed_note", "emergency physician", "2026-05-26", "AF Intake", "Patient presents with palpitations and ECG-confirmed atrial fibrillation with rapid ventricular response. Heart rate is 138 and blood pressure is stable."),
                ("progress_note", "hospitalist", "2026-05-26", "Rate Control", "Diltiazem infusion improved heart rate to the 80s. Plan is transition to metoprolol succinate and telemetry monitoring overnight."),
                ("pharmacy_note", "clinical pharmacist", "2026-05-27", "Anticoagulation Review", "CHA2DS2-VASc is 4 and hemoglobin is stable at 12.6 g/dL. Creatinine is 1.2 mg/dL, supporting standard apixaban dosing in this synthetic case."),
                ("nursing_note", "registered nurse", "2026-05-27", "Education And Fall Risk", "Patient uses a cane at baseline but had no recent falls. Nursing reviewed bleeding precautions, medication adherence, and when to seek urgent care."),
            ],
        ),
        _case(
            key="yusuf",
            case_id="case-yusuf-009",
            patient_name="Amina Yusuf",
            mrn="SYN-10216",
            age=43,
            sex="female",
            primary_concern="iron deficiency anemia workup",
            risk_level="stable",
            status="review",
            admitted_at="2026-05-27T12:00:00Z",
            active_problems=["Iron deficiency anemia", "Symptomatic fatigue", "Occult blood evaluation", "Gynecology follow-up"],
            medications=[
                {"name": "Iron sucrose", "dose": "200 mg IV daily", "status": "active"},
                {"name": "Ferrous sulfate", "dose": "325 mg every other day", "status": "planned"},
                {"name": "Pantoprazole", "dose": "40 mg daily", "status": "active"},
                {"name": "Polyethylene glycol", "dose": "as needed", "status": "bowel regimen"},
            ],
            labs=[
                {"name": "Hemoglobin", "value": "7.8 g/dL", "flag": "low"},
                {"name": "Ferritin", "value": "8 ng/mL", "flag": "low"},
                {"name": "MCV", "value": "72 fL", "flag": "microcytic"},
            ],
            vitals=[
                {"name": "Heart rate", "value": "96", "flag": "mild tachycardia"},
                {"name": "Stool guaiac", "value": "negative once", "flag": "needs context"},
            ],
            timeline=[
                {"date": "2026-05-27", "label": "Clinic labs", "detail": "Hemoglobin 7.8 prompted admission for symptomatic anemia."},
                {"date": "2026-05-27", "label": "Iron studies", "detail": "Ferritin 8 and microcytosis supported iron deficiency."},
                {"date": "2026-05-27", "label": "Bleeding screen", "detail": "No melena reported and stool guaiac negative once."},
                {"date": "2026-05-28", "label": "Iron repletion", "detail": "IV iron started with oral plan for discharge."},
                {"date": "2026-05-28", "label": "Follow-up", "detail": "GI and gynecology evaluation recommended."},
            ],
            suggested_questions=[
                "What evidence supports iron deficiency anemia?",
                "What bleeding sources still need review?",
                "Why is IV iron being used?",
                "What follow-up should be arranged after discharge?",
            ],
            notes=[
                ("admission_note", "resident physician", "2026-05-27", "Anemia Admission", "Patient reports fatigue, exertional lightheadedness, and pica. Hemoglobin is 7.8 g/dL with MCV 72 fL. She denies melena and has no hemodynamic instability."),
                ("lab_review", "hospitalist", "2026-05-27", "Iron Studies", "Ferritin is 8 ng/mL, transferrin saturation is 6 percent, and reticulocyte response is low. The pattern supports iron deficiency anemia."),
                ("progress_note", "attending physician", "2026-05-28", "Anemia Plan", "Plan is IV iron sucrose while inpatient, oral ferrous sulfate every other day after discharge, and review of constipation prevention. Transfusion is deferred unless symptoms worsen or hemoglobin drops."),
                ("consult_note", "gastroenterology", "2026-05-28", "Source Evaluation", "One stool guaiac is negative but does not complete the workup. Recommend outpatient colonoscopy and coordination with gynecology because patient reports heavy menstrual bleeding."),
            ],
        ),
        _case(
            key="kim",
            case_id="case-kim-010",
            patient_name="Grace Kim",
            mrn="SYN-10232",
            age=61,
            sex="female",
            primary_concern="post-operative fever and wound assessment",
            risk_level="watch",
            status="active",
            admitted_at="2026-05-28T08:55:00Z",
            active_problems=["Post-operative fever", "Incisional erythema", "Atelectasis prevention", "Wound culture follow-up"],
            medications=[
                {"name": "Cefazolin", "dose": "2 g IV every 8 hours", "status": "active"},
                {"name": "Acetaminophen", "dose": "650 mg as needed", "status": "active"},
                {"name": "Enoxaparin", "dose": "prophylaxis", "status": "active"},
                {"name": "Oxycodone", "dose": "low dose as needed", "status": "active"},
            ],
            labs=[
                {"name": "WBC", "value": "13.2 K/uL", "flag": "mild high"},
                {"name": "CRP", "value": "86 mg/L", "flag": "high"},
                {"name": "Creatinine", "value": "0.9 mg/dL", "flag": "normal"},
            ],
            vitals=[
                {"name": "Temperature", "value": "101.4 F -> 99.8 F", "flag": "improving"},
                {"name": "Incision", "value": "2 cm erythema, no dehiscence", "flag": "watch"},
            ],
            timeline=[
                {"date": "2026-05-26", "label": "Surgery", "detail": "Synthetic laparoscopic colectomy completed without intraoperative complication."},
                {"date": "2026-05-28", "label": "Fever", "detail": "Temperature rose to 101.4 F on post-op day 2."},
                {"date": "2026-05-28", "label": "Wound exam", "detail": "Mild erythema and scant serous drainage noted."},
                {"date": "2026-05-28", "label": "Cultures", "detail": "Wound culture obtained and cefazolin started."},
                {"date": "2026-05-29", "label": "Pulmonary care", "detail": "Incentive spirometry reinforced for atelectasis prevention."},
            ],
            suggested_questions=[
                "What evidence supports wound infection versus atelectasis?",
                "What wound findings should be monitored?",
                "What antibiotics or cultures were started?",
                "What post-operative risks remain before discharge?",
            ],
            notes=[
                ("surgery_note", "surgery resident", "2026-05-28", "Post-Op Fever", "Patient developed fever to 101.4 F on post-operative day 2. She has mild cough with low volumes on incentive spirometry and new erythema around the lower incision."),
                ("wound_note", "wound nurse", "2026-05-28", "Incision Assessment", "Lower abdominal incision has 2 cm surrounding erythema and scant serous drainage. There is no dehiscence, fluctuance, or purulence. Wound culture was obtained."),
                ("lab_review", "hospitalist", "2026-05-28", "Inflammatory Markers", "WBC is 13.2 K/uL and CRP is 86 mg/L. Creatinine is 0.9 mg/dL. Urinalysis is negative and chest x-ray shows low lung volumes without focal infiltrate."),
                ("progress_note", "attending surgeon", "2026-05-29", "Treatment Plan", "Plan is cefazolin while cultures are pending, daily wound checks, incentive spirometry, early ambulation, and reassessment for abscess if fever persists."),
            ],
        ),
        _case(
            key="hassan",
            case_id="case-hassan-011",
            patient_name="Omar Hassan",
            mrn="SYN-10247",
            age=56,
            sex="male",
            primary_concern="hypertensive urgency with renal function monitoring",
            risk_level="watch",
            status="active",
            admitted_at="2026-05-29T15:35:00Z",
            active_problems=["Hypertensive urgency", "Chronic kidney disease risk", "Medication nonadherence", "Headache without end-organ emergency"],
            medications=[
                {"name": "Amlodipine", "dose": "10 mg daily", "status": "active"},
                {"name": "Labetalol", "dose": "100 mg twice daily", "status": "active"},
                {"name": "Hydralazine", "dose": "as needed", "status": "avoid rapid drops"},
                {"name": "Acetaminophen", "dose": "650 mg as needed", "status": "active"},
            ],
            labs=[
                {"name": "Creatinine", "value": "1.6 mg/dL", "flag": "watch"},
                {"name": "Urine protein", "value": "1+", "flag": "abnormal"},
                {"name": "Troponin", "value": "negative", "flag": "reassuring"},
            ],
            vitals=[
                {"name": "Blood pressure", "value": "208/112 -> 174/94", "flag": "improving"},
                {"name": "Neuro exam", "value": "nonfocal", "flag": "reassuring"},
            ],
            timeline=[
                {"date": "2026-05-29", "label": "ED arrival", "detail": "Severe blood pressure elevation with headache but no neurologic deficit."},
                {"date": "2026-05-29", "label": "End-organ screen", "detail": "Troponin negative, neuro exam nonfocal, creatinine mildly elevated."},
                {"date": "2026-05-29", "label": "Medication history", "detail": "Patient had been out of amlodipine for two weeks."},
                {"date": "2026-05-30", "label": "BP trend", "detail": "Blood pressure improved with oral medications."},
                {"date": "2026-05-30", "label": "Renal plan", "detail": "Renal function and urine protein scheduled for follow-up."},
            ],
            suggested_questions=[
                "What evidence supports hypertensive urgency rather than emergency?",
                "What renal findings should be monitored?",
                "What medication adherence issue is documented?",
                "Why should blood pressure be lowered gradually?",
            ],
            notes=[
                ("ed_note", "emergency physician", "2026-05-29", "Hypertension Intake", "Patient presents with headache and blood pressure 208/112 after running out of amlodipine for two weeks. Neurologic exam is nonfocal and there is no chest pain."),
                ("lab_review", "hospitalist", "2026-05-29", "End-Organ Screen", "Troponin is negative, ECG has no acute ischemia, creatinine is 1.6 mg/dL, and urinalysis shows 1+ protein. No acute pulmonary edema is present."),
                ("progress_note", "attending physician", "2026-05-30", "Blood Pressure Plan", "Assessment favors hypertensive urgency rather than emergency because severe pressure elevation lacks acute neurologic, cardiac, or pulmonary end-organ damage. Plan is oral amlodipine and labetalol with gradual reduction."),
                ("case_management", "case manager", "2026-05-30", "Medication Access", "Patient reports pharmacy cost and refill timing caused missed medications. Case management arranged refill support and primary care follow-up for renal function and urine protein."),
            ],
        ),
        _case(
            key="park",
            case_id="case-park-012",
            patient_name="Linda Park",
            mrn="SYN-10259",
            age=70,
            sex="female",
            primary_concern="heart failure medication optimization",
            risk_level="stable",
            status="review",
            admitted_at="2026-05-30T09:40:00Z",
            active_problems=["Heart failure with reduced ejection fraction", "GDMT optimization", "Borderline potassium", "Recent volume overload"],
            medications=[
                {"name": "Sacubitril-valsartan", "dose": "24/26 mg twice daily", "status": "new start"},
                {"name": "Metoprolol succinate", "dose": "50 mg daily", "status": "continue"},
                {"name": "Spironolactone", "dose": "12.5 mg daily", "status": "consider with potassium monitoring"},
                {"name": "Furosemide", "dose": "40 mg oral daily", "status": "active"},
            ],
            labs=[
                {"name": "EF", "value": "32%", "flag": "reduced"},
                {"name": "Potassium", "value": "4.9 mmol/L", "flag": "watch"},
                {"name": "Creatinine", "value": "1.2 mg/dL", "flag": "stable"},
            ],
            vitals=[
                {"name": "Blood pressure", "value": "112/68", "flag": "borderline for titration"},
                {"name": "Weight", "value": "down 4 lb", "flag": "improving volume"},
            ],
            timeline=[
                {"date": "2026-05-28", "label": "HF admission", "detail": "Admitted with edema and exertional dyspnea."},
                {"date": "2026-05-29", "label": "Echo", "detail": "Ejection fraction documented at 32 percent."},
                {"date": "2026-05-29", "label": "Diuresis", "detail": "Weight decreased by 4 lb after IV diuresis."},
                {"date": "2026-05-30", "label": "GDMT review", "detail": "ARNI started and beta blocker continued."},
                {"date": "2026-05-30", "label": "Monitoring plan", "detail": "Potassium and renal function follow-up arranged."},
            ],
            suggested_questions=[
                "What evidence supports heart failure medication optimization?",
                "What GDMT changes were made?",
                "What potassium or renal monitoring matters?",
                "What volume status findings support discharge planning?",
            ],
            notes=[
                ("admission_note", "hospitalist", "2026-05-28", "Heart Failure Admission", "Patient was admitted with exertional dyspnea, ankle edema, and weight gain. She improved after IV diuresis and oxygen was not required at rest."),
                ("imaging_report", "cardiology", "2026-05-29", "Echocardiogram", "Echocardiogram shows left ventricular ejection fraction 32 percent with global hypokinesis. No severe valvular stenosis is reported."),
                ("progress_note", "cardiology", "2026-05-30", "GDMT Optimization", "Plan is to start sacubitril-valsartan at low dose, continue metoprolol succinate, and consider spironolactone only with potassium and renal monitoring."),
                ("pharmacy_note", "clinical pharmacist", "2026-05-30", "Medication Safety", "Potassium is 4.9 mmol/L and creatinine is 1.2 mg/dL. Pharmacy recommends repeat basic metabolic panel within one week after ARNI initiation and before mineralocorticoid receptor antagonist titration."),
            ],
        ),
    ]


def _case(
    *,
    key: str,
    case_id: str,
    patient_name: str,
    mrn: str,
    age: int,
    sex: str,
    primary_concern: str,
    risk_level: str,
    status: str,
    admitted_at: str,
    active_problems: list[str],
    medications: list[dict[str, str]],
    labs: list[dict[str, str]],
    vitals: list[dict[str, str]],
    timeline: list[dict[str, str]],
    suggested_questions: list[str],
    notes: list[tuple[str, str, str, str, str]],
) -> dict[str, object]:
    return {
        "id": case_id,
        "patient_name": patient_name,
        "mrn": mrn,
        "age": age,
        "sex": sex,
        "primary_concern": primary_concern,
        "risk_level": risk_level,
        "status": status,
        "admitted_at": admitted_at,
        "active_problems": active_problems,
        "medications": medications,
        "labs": labs,
        "vitals": vitals,
        "timeline": timeline,
        "suggested_questions": suggested_questions,
        "notes": [
            {
                "id": f"note-{key}-{idx:03d}",
                "note_type": note_type,
                "author_role": author_role,
                "note_date": note_date,
                "title": title,
                "body": body,
            }
            for idx, (note_type, author_role, note_date, title, body) in enumerate(notes, start=1)
        ],
    }
