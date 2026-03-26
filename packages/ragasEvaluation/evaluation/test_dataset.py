"""
EPS Assist Me evaluation dataset.

Curated questions that exercise the knowledge base across the key EPS domains:
prescribing, dispensing, FHIR APIs, CIS2 auth, SCAL requirements, and general
onboarding guidance.

Each entry contains:
    - user_input: The question sent to the bot.
    - reference:  An ideal / expected answer summary for reference-based metrics.
    - category:   A tag for grouping results in reports.
"""

EVALUATION_DATASET: list[dict] = [
    # ---- Prescription IDs ----
    {
        "user_input": (
            "If a user prescribes 6 items in a session for a patient, the GP system should "
            "separate these as 2 forms with 4 items on one and 2 items on the other. "
            "Do both prescription forms have the same Prescription ID or different IDs?"
        ),
        "reference": (
            "A prescription can have a maximum of 4 line items. Therefore, these will "
            "need to be prescribed over a minimum of 2 prescriptions. These prescriptions "
            "will have their own unique identifiers."
        ),
        "category": "prescription_ids",
    },
    # ---- CIS2 Authentication ----
    {
        "user_input": ("How do prescribers authenticate themselves to access Spine services like EPS?"),
        "reference": (
            "Prescribers authenticate through the Care Identity Service (CIS2) using their "
            "NHS provisioned CIS2 authenticator to access Spine services like EPS."
        ),
        "category": "authentication",
    },
    # ---- RBAC Controls ----
    {
        "user_input": "What are the RBAC requirements for prescribing systems?",
        "reference": (
            "Role-based access controls (RBAC) must be used to limit what users of the "
            "prescribing system can and cannot do. RBAC rules are in the National RBAC Database."
        ),
        "category": "rbac",
    },
    # ---- Repeat Dispensing Cancellation ----
    {
        "user_input": (
            "I have a query related to cancelling Repeat Dispensing courses. A patient has an "
            "ongoing RD course with 6 issues. Issue 1 is dispensed, issue 2 is with the dispenser, "
            "and issues 3-6 are still on Spine. Can the doctor cancel all issues 1-6? "
            "Can the doctor cancel only issues 3-6?"
        ),
        "reference": (
            "The Spine allows cancellation of repeat dispensing issues. Issues that are already "
            "dispensed or with the dispenser may have different cancellation outcomes compared "
            "to issues still on Spine. The cancel request can target specific issues."
        ),
        "category": "repeat_dispensing",
    },
    # ---- Controlled Drugs ----
    {
        "user_input": "Can Schedule 1 controlled drugs be prescribed using EPS?",
        "reference": ("Schedule 1 controlled drugs must not be prescribed using EPS."),
        "category": "controlled_drugs",
    },
    # ---- Nomination Management ----
    {
        "user_input": ("How can a prescriber change a patient's nominated dispensing site?"),
        "reference": (
            "Prescribers can add, update, or remove a patient's nomination on PDS at the "
            "patient's request. They can change the dispenser's ODS code and the type of dispenser."
        ),
        "category": "nominations",
    },
    # ---- FHIR API / Prescription Structure ----
    {
        "user_input": (
            "What patient details must be included on an EPS prescription according " "to the FHIR API schema?"
        ),
        "reference": (
            "The prescription must include the patient's NHS number, usual name, gender, " "and date of birth."
        ),
        "category": "fhir_api",
    },
    # ---- Prescription Types ----
    {
        "user_input": ("What prescription treatment types can prescribers choose from in " "Secondary Care?"),
        "reference": (
            "Prescribers in Secondary Care can choose: 0001 Acute (Mandatory), "
            "0002 Repeat Prescribing (optional), and 0003 Electronic Repeat Dispensing "
            "(eRD) (optional depending on use case)."
        ),
        "category": "prescription_types",
    },
    # ---- Deceased Patients ----
    {
        "user_input": ("Can I create an EPS prescription for a patient who has been marked " "as deceased on PDS?"),
        "reference": (
            "No. You must not create a prescription using EPS for patients that have " "been marked as deceased on PDS."
        ),
        "category": "patient_eligibility",
    },
    # ---- Error Handling ----
    {
        "user_input": ("What are the recommended error handling strategies when calling " "NHS England APIs?"),
        "reference": (
            "Applications should examine the return status code, implement retry strategies "
            "such as exponential backoff, and incorporate wait/loop code with appropriate "
            "delays before retrying. For end users, a lower initial retry interval of 200ms "
            "with a maximum of 3 seconds is recommended."
        ),
        "category": "error_handling",
    },
    # ---- Sensitive Patients ----
    {
        "user_input": ("What should happen when prescribing for a patient with a sensitive " "status on PDS?"),
        "reference": (
            "A prescription must not be created using EPS for patients that have " "a sensitive status on PDS."
        ),
        "category": "patient_eligibility",
    },
    # ---- dm+d Requirements ----
    {
        "user_input": (
            "What happens if a medication is not listed in the dm+d? Can it still " "be prescribed via EPS?"
        ),
        "reference": (
            "Medication not listed within dm+d must not be prescribed via EPS. "
            "FP10s must be used for items not in dm+d and not mapped from a local "
            "proprietary database. Medication may be split across electronic and "
            "FP10 prescriptions."
        ),
        "category": "dmd",
    },
]
