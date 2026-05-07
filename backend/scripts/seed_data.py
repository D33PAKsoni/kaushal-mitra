"""
Seed data — 20 realistic Karnataka candidates.
4 districts: Belagavi, Mysuru, Dharwad, Bengaluru Rural
2 trades: electrician, plumber
All 5 fitment categories represented
1 duplicate pair (Raju/Rajesh — same face embedding)
1 fraud flag (face not detected)
"""

from datetime import datetime, timedelta
import random

_base = datetime(2026, 5, 3, 9, 0, 0)

def _dt(minutes_offset):
    return (_base + timedelta(minutes=minutes_offset)).isoformat()

SEEDED_CANDIDATES = [
    # ── Belagavi — Electrician ─────────────────────────────
    {
        "session_id": "seed-001", "name": "Ramesh Patil", "trade": "electrician",
        "district": "Belagavi", "language": "kn",
        "fitment_category": "job_ready", "composite_score": 8.4,
        "domain_score": 8.8, "communication_score": 7.8, "integrity_score": 10.0,
        "is_flagged": False, "is_shortlisted": True, "flag_reason": None,
        "reason_card_en": "Excellent knowledge of wiring and safety standards. Ready for immediate placement.",
        "reason_card_kn": "ವೈರಿಂಗ್ ಮತ್ತು ಸುರಕ್ಷತಾ ಮಾನದಂಡಗಳ ಅತ್ಯುತ್ತಮ ಜ್ಞಾನ. ತಕ್ಷಣ ನಿಯೋಜನೆಗೆ ಸಿದ್ಧ.",
        "created_at": _dt(0),
    },
    {
        "session_id": "seed-002", "name": "Suresh Desai", "trade": "electrician",
        "district": "Belagavi", "language": "kn",
        "fitment_category": "trainable", "composite_score": 6.3,
        "domain_score": 6.5, "communication_score": 6.0, "integrity_score": 10.0,
        "is_flagged": False, "is_shortlisted": False, "flag_reason": None,
        "reason_card_en": "Good practical knowledge, needs theory training on MCB sizing.",
        "reason_card_kn": "ಉತ್ತಮ ಪ್ರಾಯೋಗಿಕ ಜ್ಞಾನ, MCB ಸೈಜಿಂಗ್ ತರಬೇತಿ ಅಗತ್ಯ.",
        "created_at": _dt(15),
    },
    {
        "session_id": "seed-003", "name": "Vijay Kulkarni", "trade": "electrician",
        "district": "Belagavi", "language": "kn",
        "fitment_category": "requires_training", "composite_score": 4.8,
        "domain_score": 4.5, "communication_score": 5.2, "integrity_score": 9.0,
        "is_flagged": False, "is_shortlisted": False, "flag_reason": None,
        "reason_card_en": "Limited knowledge of three-phase systems. Recommend basic electrician course.",
        "reason_card_kn": "ತ್ರಿ-ಫೇಸ್ ಸಿಸ್ಟಂ ಜ್ಞಾನ ಕಡಿಮೆ. ಮೂಲ ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ ಕೋರ್ಸ್ ಶಿಫಾರಸು.",
        "created_at": _dt(30),
    },
    {
        "session_id": "seed-004", "name": "Priya Hiremath", "trade": "electrician",
        "district": "Belagavi", "language": "en",
        "fitment_category": "job_ready", "composite_score": 8.9,
        "domain_score": 9.2, "communication_score": 8.4, "integrity_score": 10.0,
        "is_flagged": False, "is_shortlisted": True, "flag_reason": None,
        "reason_card_en": "Exceptional candidate. Strong safety awareness and IS standards knowledge.",
        "reason_card_kn": "ಅಸಾಧಾರಣ ಅಭ್ಯರ್ಥಿ. ಉತ್ತಮ ಸುರಕ್ಷತಾ ಜಾಗೃತಿ.",
        "created_at": _dt(45),
    },

    # ── Mysuru — Plumber ──────────────────────────────────
    {
        "session_id": "seed-005", "name": "Mohan Gowda", "trade": "plumber",
        "district": "Mysuru", "language": "kn",
        "fitment_category": "job_ready", "composite_score": 8.1,
        "domain_score": 8.3, "communication_score": 7.8, "integrity_score": 10.0,
        "is_flagged": False, "is_shortlisted": True, "flag_reason": None,
        "reason_card_en": "Strong knowledge of pipe sizing and septic systems. Job ready.",
        "reason_card_kn": "ಪೈಪ್ ಸೈಜಿಂಗ್ ಮತ್ತು ಸೆಪ್ಟಿಕ್ ಸಿಸ್ಟಂ ಉತ್ತಮ ಜ್ಞಾನ.",
        "created_at": _dt(60),
    },
    {
        "session_id": "seed-006", "name": "Kavitha Nair", "trade": "plumber",
        "district": "Mysuru", "language": "en",
        "fitment_category": "trainable", "composite_score": 6.7,
        "domain_score": 7.0, "communication_score": 6.2, "integrity_score": 10.0,
        "is_flagged": False, "is_shortlisted": False, "flag_reason": None,
        "reason_card_en": "Good practical experience. Needs training on NBC plumbing standards.",
        "reason_card_kn": "ಉತ್ತಮ ಪ್ರಾಯೋಗಿಕ ಅನುಭವ. NBC ಮಾನದಂಡ ತರಬೇತಿ ಅಗತ್ಯ.",
        "created_at": _dt(75),
    },
    {
        "session_id": "seed-007", "name": "Ravi Shankar", "trade": "plumber",
        "district": "Mysuru", "language": "kn",
        "fitment_category": "not_suitable", "composite_score": 2.8,
        "domain_score": 2.5, "communication_score": 3.2, "integrity_score": 8.0,
        "is_flagged": False, "is_shortlisted": False, "flag_reason": None,
        "reason_card_en": "Very limited knowledge of basic plumbing. Recommend starting from foundation level.",
        "reason_card_kn": "ಮೂಲಭೂತ ಪ್ಲಂಬಿಂಗ್ ಜ್ಞಾನ ತುಂಬಾ ಕಡಿಮೆ. ಆಧಾರ ಮಟ್ಟದಿಂದ ಪ್ರಾರಂಭಿಸಲು ಶಿಫಾರಸು.",
        "created_at": _dt(90),
    },
    {
        "session_id": "seed-008", "name": "Lakshmi Devi", "trade": "plumber",
        "district": "Mysuru", "language": "kn",
        "fitment_category": "requires_training", "composite_score": 5.2,
        "domain_score": 5.0, "communication_score": 5.5, "integrity_score": 9.5,
        "is_flagged": False, "is_shortlisted": False, "flag_reason": None,
        "reason_card_en": "Average performance. Enroll in DDUGKY plumber advanced module.",
        "reason_card_kn": "ಸರಾಸರಿ ಪ್ರದರ್ಶನ. DDUGKY ಪ್ಲಂಬರ್ ಮಾಡ್ಯೂಲ್‌ನಲ್ಲಿ ಸೇರಿ.",
        "created_at": _dt(105),
    },

    # ── Dharwad — Electrician ─────────────────────────────
    {
        "session_id": "seed-009", "name": "Arun Kumar", "trade": "electrician",
        "district": "Dharwad", "language": "kn",
        "fitment_category": "trainable", "composite_score": 6.1,
        "domain_score": 6.0, "communication_score": 6.3, "integrity_score": 10.0,
        "is_flagged": False, "is_shortlisted": False, "flag_reason": None,
        "reason_card_en": "Decent practical skills. Needs theory on load calculation.",
        "reason_card_kn": "ಉಚಿತ ಪ್ರಾಯೋಗಿಕ ಕೌಶಲ. ಲೋಡ್ ಲೆಕ್ಕಾಚಾರ ಸಿದ್ಧಾಂತ ಅಗತ್ಯ.",
        "created_at": _dt(120),
    },
    {
        "session_id": "seed-010", "name": "Meena Joshi", "trade": "electrician",
        "district": "Dharwad", "language": "en",
        "fitment_category": "job_ready", "composite_score": 8.6,
        "domain_score": 8.9, "communication_score": 8.1, "integrity_score": 10.0,
        "is_flagged": False, "is_shortlisted": True, "flag_reason": None,
        "reason_card_en": "Outstanding knowledge of industrial electrical systems. Immediate placement recommended.",
        "reason_card_kn": "ಕೈಗಾರಿಕಾ ವಿದ್ಯುತ್ ವ್ಯವಸ್ಥೆಗಳ ಅತ್ಯುತ್ತಮ ಜ್ಞಾನ.",
        "created_at": _dt(135),
    },
    # ── DUPLICATE PAIR — Raju / Rajesh ────────────────────
    {
        "session_id": "seed-011", "name": "Raju Lamani", "trade": "electrician",
        "district": "Dharwad", "language": "kn",
        "fitment_category": "review_required", "composite_score": 7.2,
        "domain_score": 7.5, "communication_score": 6.8, "integrity_score": 6.0,
        "is_flagged": True, "is_shortlisted": False,
        "flag_reason": "Possible duplicate: face similarity 94% with seed-012 (Rajesh Lamani)",
        "reason_card_en": "Flagged for manual review — possible duplicate registration detected.",
        "reason_card_kn": "ಹಸ್ತಚಾಲಿತ ಪರಿಶೀಲನೆಗೆ ಫ್ಲ್ಯಾಗ್ — ನಕಲು ನೋಂದಣಿ ಪತ್ತೆ.",
        "created_at": _dt(150),
    },
    {
        "session_id": "seed-012", "name": "Rajesh Lamani", "trade": "plumber",
        "district": "Dharwad", "language": "kn",
        "fitment_category": "review_required", "composite_score": 7.0,
        "domain_score": 7.2, "communication_score": 6.6, "integrity_score": 6.0,
        "is_flagged": True, "is_shortlisted": False,
        "flag_reason": "Possible duplicate: face similarity 94% with seed-011 (Raju Lamani)",
        "reason_card_en": "Flagged for manual review — possible duplicate registration detected.",
        "reason_card_kn": "ಹಸ್ತಚಾಲಿತ ಪರಿಶೀಲನೆಗೆ ಫ್ಲ್ಯಾಗ್ — ನಕಲು ನೋಂದಣಿ ಪತ್ತೆ.",
        "created_at": _dt(165),
    },

    # ── Bengaluru Rural — Mixed ───────────────────────────
    {
        "session_id": "seed-013", "name": "Ganesh Reddy", "trade": "electrician",
        "district": "Bengaluru Rural", "language": "en",
        "fitment_category": "job_ready", "composite_score": 9.1,
        "domain_score": 9.4, "communication_score": 8.6, "integrity_score": 10.0,
        "is_flagged": False, "is_shortlisted": True, "flag_reason": None,
        "reason_card_en": "Top performer. Recommend direct placement with KPTCL contractors.",
        "reason_card_kn": "ಅತ್ಯುತ್ತಮ ಪ್ರದರ್ಶನ. KPTCL ಗುತ್ತಿಗೆದಾರರೊಂದಿಗೆ ನಿಯೋಜನೆ ಶಿಫಾರಸು.",
        "created_at": _dt(180),
    },
    # ── FRAUD FLAG — camera not present ──────────────────
    {
        "session_id": "seed-014", "name": "Unknown Candidate", "trade": "plumber",
        "district": "Bengaluru Rural", "language": "kn",
        "fitment_category": "review_required", "composite_score": 7.8,
        "domain_score": 8.0, "communication_score": 7.4, "integrity_score": 0.0,
        "is_flagged": True, "is_shortlisted": False,
        "flag_reason": "Camera not active during interview — integrity unverified",
        "reason_card_en": "Flagged: camera was not detected during the interview. Identity unverified.",
        "reason_card_kn": "ಫ್ಲ್ಯಾಗ್: ಸಂದರ್ಶನದ ಸಮಯದಲ್ಲಿ ಕ್ಯಾಮೆರಾ ಕಂಡುಬಂದಿಲ್ಲ.",
        "created_at": _dt(195),
    },
    {
        "session_id": "seed-015", "name": "Savitha Kumari", "trade": "plumber",
        "district": "Bengaluru Rural", "language": "kn",
        "fitment_category": "trainable", "composite_score": 6.5,
        "domain_score": 6.8, "communication_score": 6.0, "integrity_score": 10.0,
        "is_flagged": False, "is_shortlisted": False, "flag_reason": None,
        "reason_card_en": "Good basic knowledge. Enroll in DDUGKY advanced plumber course.",
        "reason_card_kn": "ಉಚಿತ ಮೂಲ ಜ್ಞಾನ. DDUGKY ಮುಂದುವರಿದ ಪ್ಲಂಬರ್ ಕೋರ್ಸ್‌ನಲ್ಲಿ ಸೇರಿ.",
        "created_at": _dt(210),
    },
    {
        "session_id": "seed-016", "name": "Basavaraj Angadi", "trade": "electrician",
        "district": "Bengaluru Rural", "language": "kn",
        "fitment_category": "requires_training", "composite_score": 4.5,
        "domain_score": 4.2, "communication_score": 5.0, "integrity_score": 9.0,
        "is_flagged": False, "is_shortlisted": False, "flag_reason": None,
        "reason_card_en": "Basic understanding only. Recommend 3-month ITI refresher course.",
        "reason_card_kn": "ಮೂಲ ತಿಳುವಳಿಕೆ ಮಾತ್ರ. 3 ತಿಂಗಳ ITI ರಿಫ್ರೆಶರ್ ಕೋರ್ಸ್ ಶಿಫಾರಸು.",
        "created_at": _dt(225),
    },
    {
        "session_id": "seed-017", "name": "Deepa Nagaraj", "trade": "plumber",
        "district": "Mysuru", "language": "en",
        "fitment_category": "job_ready", "composite_score": 8.3,
        "domain_score": 8.6, "communication_score": 7.8, "integrity_score": 10.0,
        "is_flagged": False, "is_shortlisted": True, "flag_reason": None,
        "reason_card_en": "Strong candidate with commercial plumbing experience. Shortlisted.",
        "reason_card_kn": "ವಾಣಿಜ್ಯ ಪ್ಲಂಬಿಂಗ್ ಅನುಭವ ಉತ್ತಮ. ಶಾರ್ಟ್‌ಲಿಸ್ಟ್.",
        "created_at": _dt(240),
    },
    {
        "session_id": "seed-018", "name": "Santosh Bhovi", "trade": "electrician",
        "district": "Belagavi", "language": "kn",
        "fitment_category": "not_suitable", "composite_score": 1.9,
        "domain_score": 1.5, "communication_score": 2.5, "integrity_score": 7.0,
        "is_flagged": False, "is_shortlisted": False, "flag_reason": None,
        "reason_card_en": "Not suitable at this time. Recommend attending basic electrical safety course first.",
        "reason_card_kn": "ಈ ಸಮಯದಲ್ಲಿ ಸೂಕ್ತವಲ್ಲ. ಮೊದಲು ಮೂಲ ವಿದ್ಯುತ್ ಸುರಕ್ಷತಾ ಕೋರ್ಸ್ ಮಾಡಿ.",
        "created_at": _dt(255),
    },
    {
        "session_id": "seed-019", "name": "Nagamma Siddappa", "trade": "plumber",
        "district": "Dharwad", "language": "kn",
        "fitment_category": "trainable", "composite_score": 6.9,
        "domain_score": 7.1, "communication_score": 6.5, "integrity_score": 10.0,
        "is_flagged": False, "is_shortlisted": False, "flag_reason": None,
        "reason_card_en": "Good practical skills. Theory gap in water pressure calculations.",
        "reason_card_kn": "ಉಚಿತ ಪ್ರಾಯೋಗಿಕ ಕೌಶಲ. ನೀರಿನ ಒತ್ತಡ ಲೆಕ್ಕಾಚಾರ ಸಿದ್ಧಾಂತ ಅಗತ್ಯ.",
        "created_at": _dt(270),
    },
    {
        "session_id": "seed-020", "name": "Harish Talwar", "trade": "electrician",
        "district": "Bengaluru Rural", "language": "en",
        "fitment_category": "requires_training", "composite_score": 5.5,
        "domain_score": 5.3, "communication_score": 5.8, "integrity_score": 9.5,
        "is_flagged": False, "is_shortlisted": False, "flag_reason": None,
        "reason_card_en": "Some knowledge of residential wiring. Needs hands-on training with live panels.",
        "reason_card_kn": "ವಸತಿ ವೈರಿಂಗ್ ಬಗ್ಗೆ ಸ್ವಲ್ಪ ಜ್ಞಾನ. ಲೈವ್ ಪ್ಯಾನೆಲ್ ಕೆಲಸ ತರಬೇತಿ ಅಗತ್ಯ.",
        "created_at": _dt(285),
    },
]
