"""
Static data for regulation catalog seeding and question migration.
No DB imports — imported by db.py.
"""
from __future__ import annotations

REGULATIONS_SEED = [
    {
        "code": "eu_ai_act",
        "name": "EU AI Act",
        "jurisdiction": "EU",
        "description": (
            "Regulation (EU) 2024/1689 on Artificial Intelligence — the world's first "
            "comprehensive legal framework for AI, establishing risk-based obligations for "
            "providers and deployers of AI systems in the EU."
        ),
        "deadline": "2026-08-02",
        "is_active": True,
    },
    {
        "code": "gdpr",
        "name": "GDPR",
        "jurisdiction": "EU",
        "description": (
            "General Data Protection Regulation — the EU's primary data protection law "
            "governing how personal data is collected, processed, and protected. Applies "
            "to all organisations processing EU residents' data."
        ),
        "deadline": None,
        "is_active": True,
    },
    {
        "code": "nist_ai_rmf",
        "name": "NIST AI RMF",
        "jurisdiction": "US",
        "description": (
            "NIST AI Risk Management Framework — voluntary US federal guidance for "
            "identifying, assessing, and managing AI risks across four functions: "
            "GOVERN, MAP, MEASURE, MANAGE."
        ),
        "deadline": None,
        "is_active": True,
    },
    {
        "code": "iso_42001",
        "name": "ISO 42001",
        "jurisdiction": "International",
        "description": (
            "ISO/IEC 42001:2023 — the first international standard specifying requirements "
            "for an AI Management System (AIMS), covering responsible AI development, "
            "deployment, and continual improvement."
        ),
        "deadline": None,
        "is_active": False,
    },
]

# Maps original QUESTIONS_INTERNAL id → article tags for EU AI Act migration
EUAIACT_ARTICLE_TAGS: dict[str, list[str]] = {
    "q1": ["Art.3", "Art.5"],
    "q2": ["Art.6", "Annex III"],
    "q3": ["Art.9"],
    "q4": ["Art.10"],
    "q5": ["Art.13"],
    "q6": ["Art.14"],
    "q7": ["Annex III"],
    "q8": ["Annex III"],
    "q9": ["Art.16", "Art.17"],
    "q10": ["Art.11", "Art.12"],
    "q11": ["Art.43"],
    "q12": ["Art.49"],
    "q13": ["Art.72"],
    "q14": ["Art.73"],
    "q15": ["Art.26"],
    "q16": ["Art.29"],
    "q17": ["Art.4"],
    "q18": ["Art.28", "Art.25"],
    "q19": ["Art.53"],
    "q20": ["Art.17", "Art.49"],
}

def _o(*items: tuple[str, str, float]) -> list[dict]:
    return [{"value": v, "label": lab, "points": pts} for v, lab, pts in items]


GDPR_QUESTIONS: list[dict] = [
    # Section 1 — Lawful Basis & Consent
    {
        "question_id": "gdpr_q1",
        "section": 1,
        "section_title": "Lawful Basis & Consent",
        "question_text": "Does your organisation have a documented lawful basis for every personal data processing activity?",
        "question_type": "single",
        "options": _o(
            ("yes_fully", "Yes, fully documented", 1.0),
            ("partial", "Some activities documented", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["Art.6"],
        "show_if_json": None,
        "order_index": 1,
    },
    {
        "question_id": "gdpr_q2",
        "section": 1,
        "section_title": "Lawful Basis & Consent",
        "question_text": (
            "Where you rely on consent as your lawful basis, is it freely given, specific, "
            "informed, and unambiguous — and can individuals withdraw it as easily as they gave it?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes", "Yes", 1.0),
            ("partial", "Partially", 0.5),
            ("no", "No", 0.0),
            ("not_applicable", "Not applicable — we do not rely on consent", 1.0),
        ),
        "article_tags": ["Art.7"],
        "show_if_json": None,
        "order_index": 2,
    },
    {
        "question_id": "gdpr_q3",
        "section": 1,
        "section_title": "Lawful Basis & Consent",
        "question_text": "Do you maintain Records of Processing Activities (RoPA) covering all processing operations?",
        "question_type": "single",
        "options": _o(
            ("yes_complete", "Yes, complete and current", 1.0),
            ("in_progress", "In progress", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["Art.30"],
        "show_if_json": None,
        "order_index": 3,
    },
    {
        "question_id": "gdpr_q4",
        "section": 1,
        "section_title": "Lawful Basis & Consent",
        "question_text": "Which special categories of personal data does your organisation process?",
        "question_type": "multi",
        "options": _o(
            ("biometric", "Biometric data", 0.0),
            ("health", "Health / medical data", 0.0),
            ("genetic", "Genetic data", 0.0),
            ("racial_ethnic", "Racial or ethnic origin", 0.0),
            ("none", "None of the above", 0.0),
        ),
        "article_tags": ["Art.9"],
        "show_if_json": None,
        "order_index": 4,
    },
    # Section 2 — Data Subject Rights
    {
        "question_id": "gdpr_q5",
        "section": 2,
        "section_title": "Data Subject Rights",
        "question_text": "Can your organisation respond to Subject Access Requests (SARs) within 30 days?",
        "question_type": "single",
        "options": _o(
            ("yes_process", "Yes, with a documented process", 1.0),
            ("ad_hoc", "Ad hoc / informal", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["Art.15"],
        "show_if_json": None,
        "order_index": 5,
    },
    {
        "question_id": "gdpr_q6",
        "section": 2,
        "section_title": "Data Subject Rights",
        "question_text": (
            "Do you have a process to honour the right to erasure ('right to be forgotten') "
            "including across third-party processors?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes", "Yes", 1.0),
            ("partial", "Partial", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["Art.17"],
        "show_if_json": None,
        "order_index": 6,
    },
    {
        "question_id": "gdpr_q7",
        "section": 2,
        "section_title": "Data Subject Rights",
        "question_text": "Can individuals port their data in a machine-readable format (JSON/CSV) on request?",
        "question_type": "single",
        "options": _o(
            ("yes", "Yes, automated", 1.0),
            ("manual_only", "Manual process only", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["Art.20"],
        "show_if_json": None,
        "order_index": 7,
    },
    # Section 3 — Security & Breach Response
    {
        "question_id": "gdpr_q8",
        "section": 3,
        "section_title": "Security & Breach Response",
        "question_text": (
            "Has your organisation implemented technical and organisational measures appropriate "
            "to the risk (encryption, pseudonymisation, access controls)?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_documented", "Yes, documented and reviewed", 1.0),
            ("partial", "Partial", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["Art.32"],
        "show_if_json": None,
        "order_index": 8,
    },
    {
        "question_id": "gdpr_q9",
        "section": 3,
        "section_title": "Security & Breach Response",
        "question_text": (
            "Do you have a data breach detection and notification procedure that meets the "
            "72-hour supervisory authority reporting requirement?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_tested", "Yes, tested and rehearsed", 1.0),
            ("written_untested", "Written but not tested", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["Art.33", "Art.34"],
        "show_if_json": None,
        "order_index": 9,
    },
    {
        "question_id": "gdpr_q10",
        "section": 3,
        "section_title": "Security & Breach Response",
        "question_text": (
            "Are Data Processing Agreements (DPAs) in place with all processors who handle "
            "personal data on your behalf?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_all", "Yes, all processors covered", 1.0),
            ("most", "Most but not all", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["Art.28"],
        "show_if_json": None,
        "order_index": 10,
    },
    # Section 4 — Privacy by Design & DPIAs
    {
        "question_id": "gdpr_q11",
        "section": 4,
        "section_title": "Privacy by Design & DPIAs",
        "question_text": (
            "Is privacy by design and by default embedded in your product development lifecycle?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_formal", "Yes, formally embedded", 1.0),
            ("informal", "Informal / ad hoc", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["Art.25"],
        "show_if_json": None,
        "order_index": 11,
    },
    {
        "question_id": "gdpr_q12",
        "section": 4,
        "section_title": "Privacy by Design & DPIAs",
        "question_text": (
            "Do you conduct Data Protection Impact Assessments (DPIAs) before deploying "
            "high-risk processing activities (AI profiling, large-scale surveillance, biometrics)?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_always", "Yes, always for high-risk activities", 1.0),
            ("sometimes", "Sometimes", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["Art.35"],
        "show_if_json": None,
        "order_index": 12,
    },
    {
        "question_id": "gdpr_q13",
        "section": 4,
        "section_title": "Privacy by Design & DPIAs",
        "question_text": (
            "Have you appointed a Data Protection Officer (DPO) where required, "
            "or assessed whether one is required?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_appointed", "Yes, DPO appointed", 1.0),
            ("assessed_not_required", "Assessed — DPO not required", 1.0),
            ("no", "No assessment done", 0.0),
        ),
        "article_tags": ["Art.37"],
        "show_if_json": None,
        "order_index": 13,
    },
    # Section 5 — Transfers & Governance
    {
        "question_id": "gdpr_q14",
        "section": 5,
        "section_title": "Transfers & Governance",
        "question_text": (
            "Are international data transfers (outside EEA) covered by an appropriate "
            "transfer mechanism (SCCs, adequacy decision, BCRs)?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes", "Yes, covered", 1.0),
            ("partial", "Some transfers not covered", 0.5),
            ("no", "No", 0.0),
            ("no_transfers", "No international transfers", 1.0),
        ),
        "article_tags": ["Art.44", "Art.46"],
        "show_if_json": None,
        "order_index": 14,
    },
    {
        "question_id": "gdpr_q15",
        "section": 5,
        "section_title": "Transfers & Governance",
        "question_text": (
            "Does your organisation have a named individual accountable for GDPR compliance "
            "with board-level visibility?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_board", "Yes, with board-level visibility", 1.0),
            ("yes_no_board", "Yes, but limited board visibility", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["Art.5", "Art.24"],
        "show_if_json": None,
        "order_index": 15,
    },
]


NIST_QUESTIONS: list[dict] = [
    # Section 1 — GOVERN
    {
        "question_id": "nist_q1",
        "section": 1,
        "section_title": "GOVERN",
        "question_text": (
            "Does your organisation have a formal AI risk management policy with defined "
            "roles, responsibilities, and accountability?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_documented", "Yes, documented and approved", 1.0),
            ("in_development", "In development", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["GOVERN-1.1", "GOVERN-1.2"],
        "show_if_json": None,
        "order_index": 1,
    },
    {
        "question_id": "nist_q2",
        "section": 1,
        "section_title": "GOVERN",
        "question_text": (
            "Is AI risk management integrated into your organisation-wide enterprise risk "
            "management (ERM) process?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_integrated", "Yes, fully integrated", 1.0),
            ("partial", "Partially integrated", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["GOVERN-1.4"],
        "show_if_json": None,
        "order_index": 2,
    },
    {
        "question_id": "nist_q3",
        "section": 1,
        "section_title": "GOVERN",
        "question_text": (
            "Do you have a process for assessing the trustworthiness characteristics "
            "(fairness, explainability, privacy, security) of AI systems before deployment?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_formal", "Yes, formal process", 1.0),
            ("ad_hoc", "Ad hoc", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["GOVERN-2.1", "GOVERN-2.2"],
        "show_if_json": None,
        "order_index": 3,
    },
    {
        "question_id": "nist_q4",
        "section": 1,
        "section_title": "GOVERN",
        "question_text": (
            "Are AI development teams trained on responsible AI principles and the "
            "organisation's AI risk policy?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_all", "Yes, all teams trained", 1.0),
            ("some", "Some teams trained", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["GOVERN-3.1", "GOVERN-4.1"],
        "show_if_json": None,
        "order_index": 4,
    },
    # Section 2 — MAP
    {
        "question_id": "nist_q5",
        "section": 2,
        "section_title": "MAP",
        "question_text": (
            "Do you categorise AI use cases by their potential negative impact on individuals, "
            "groups, or society before development begins?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_structured", "Yes, structured categorisation", 1.0),
            ("informal", "Informal assessment", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["MAP-1.1", "MAP-1.5"],
        "show_if_json": None,
        "order_index": 5,
    },
    {
        "question_id": "nist_q6",
        "section": 2,
        "section_title": "MAP",
        "question_text": (
            "Do you document the intended purpose, context of use, and foreseeable misuse "
            "scenarios for each AI system?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_all", "Yes, for all systems", 1.0),
            ("some", "For some systems", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["MAP-1.6", "MAP-2.1"],
        "show_if_json": None,
        "order_index": 6,
    },
    {
        "question_id": "nist_q7",
        "section": 2,
        "section_title": "MAP",
        "question_text": (
            "Which AI trustworthiness properties do you formally evaluate before deployment?"
        ),
        "question_type": "multi",
        "options": _o(
            ("fairness", "Fairness", 0.25),
            ("explainability", "Explainability", 0.25),
            ("privacy", "Privacy", 0.25),
            ("robustness", "Robustness", 0.25),
            ("security", "Security", 0.25),
            ("safety", "Safety", 0.25),
            ("none", "None formally evaluated", 0.0),
        ),
        "article_tags": ["MAP-5.1", "MAP-5.2"],
        "show_if_json": None,
        "order_index": 7,
    },
    # Section 3 — MEASURE
    {
        "question_id": "nist_q8",
        "section": 3,
        "section_title": "MEASURE",
        "question_text": (
            "Do you have quantitative or qualitative metrics to measure AI risks "
            "(bias rates, error rates, drift, adversarial robustness)?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_quantitative", "Yes, quantitative metrics", 1.0),
            ("qualitative_only", "Qualitative only", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["MEASURE-1.1", "MEASURE-2.1"],
        "show_if_json": None,
        "order_index": 8,
    },
    {
        "question_id": "nist_q9",
        "section": 3,
        "section_title": "MEASURE",
        "question_text": (
            "Are AI systems monitored in production for performance degradation, data drift, "
            "or unexpected behaviour after deployment?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_automated", "Yes, automated monitoring", 1.0),
            ("manual_periodic", "Manual / periodic checks", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["MEASURE-2.7", "MEASURE-2.8"],
        "show_if_json": None,
        "order_index": 9,
    },
    {
        "question_id": "nist_q10",
        "section": 3,
        "section_title": "MEASURE",
        "question_text": (
            "Do you conduct red-teaming, adversarial testing, or independent evaluations "
            "of high-risk AI systems?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_regular", "Yes, regularly", 1.0),
            ("once_at_launch", "Once at launch only", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["MEASURE-2.5", "MEASURE-2.6"],
        "show_if_json": None,
        "order_index": 10,
    },
    {
        "question_id": "nist_q11",
        "section": 3,
        "section_title": "MEASURE",
        "question_text": (
            "Are AI risk measurement results documented and communicated to decision-makers "
            "and affected stakeholders?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_formal", "Yes, formal reporting", 1.0),
            ("informal", "Informal communication", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["MEASURE-4.1", "MEASURE-4.2"],
        "show_if_json": None,
        "order_index": 11,
    },
    # Section 4 — MANAGE
    {
        "question_id": "nist_q12",
        "section": 4,
        "section_title": "MANAGE",
        "question_text": (
            "Do you have a defined process for responding to AI incidents — including "
            "rollback, notification, and root cause analysis?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_tested", "Yes, tested and documented", 1.0),
            ("written_untested", "Written but not tested", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["MANAGE-2.2", "MANAGE-2.4"],
        "show_if_json": None,
        "order_index": 12,
    },
    {
        "question_id": "nist_q13",
        "section": 4,
        "section_title": "MANAGE",
        "question_text": (
            "Can your organisation decommission or override an AI system quickly if a "
            "significant risk is identified in production?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_automated", "Yes, automated kill-switch", 1.0),
            ("manual_possible", "Manual process possible", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["MANAGE-2.1"],
        "show_if_json": None,
        "order_index": 13,
    },
    {
        "question_id": "nist_q14",
        "section": 4,
        "section_title": "MANAGE",
        "question_text": (
            "Do you track and learn from near-misses and AI failures across projects "
            "(lessons-learned register)?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes_formal", "Yes, formal register", 1.0),
            ("informal", "Informal tracking", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["MANAGE-3.1", "MANAGE-3.2"],
        "show_if_json": None,
        "order_index": 14,
    },
    {
        "question_id": "nist_q15",
        "section": 4,
        "section_title": "MANAGE",
        "question_text": (
            "Are third-party AI components, models, and datasets subject to the same risk "
            "assessment process as internally developed AI?"
        ),
        "question_type": "single",
        "options": _o(
            ("yes", "Yes", 1.0),
            ("partial", "Partial", 0.5),
            ("no", "No", 0.0),
        ),
        "article_tags": ["MANAGE-1.3"],
        "show_if_json": None,
        "order_index": 15,
    },
]
