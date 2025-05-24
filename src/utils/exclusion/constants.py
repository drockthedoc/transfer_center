"""
Constants for the exclusion criteria parser.

This module contains mapping dictionaries and keyword lists used for
parsing and categorizing exclusion criteria.
"""

import os

# Paths
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "exclusion_criteria.json")

# PDF files to convert
PDF_FILES = {
    "austin": os.path.join(DATA_DIR, "Austin-Transfer-Exclusion-Criteria.pdf"),
    "community": os.path.join(
        DATA_DIR, "Community-Campus-Exclusion-Criteria-4_2024-v1.pdf"
    ),
}

# Department/specialty mapping for standardization
DEPARTMENT_MAPPING = {
    # General departments
    "administrative": ["administrative", "admin", "general"],
    "nicu": ["nicu", "neonatal", "neonate", "infant", "newborn"],
    "picu": ["picu", "intensive care", "critical care"],
    # Medical specialties
    "cardiology": ["cardiology", "cardiac", "heart", "cardiovascular"],
    "pulmonary": [
        "pulmonary",
        "respiratory",
        "breathing",
        "lung",
        "airway",
        "pneumonia",
        "ventilator",
        "bipap",
        "cpap",
    ],
    "neurology": [
        "neurology",
        "neurological",
        "brain",
        "seizure",
        "stroke",
        "cerebral",
        "neuro",
        "eeg",
    ],
    "gastroenterology": [
        "gastroenterology",
        "gastrointestinal",
        "gi",
        "digestive",
        "stomach",
        "intestinal",
        "liver",
    ],
    "orthopedics": [
        "orthopedics",
        "ortho",
        "fracture",
        "bone",
        "joint",
        "skeletal",
    ],
    "nephrology": [
        "nephrology",
        "renal",
        "kidney",
        "dialysis",
        "creatinine",
    ],
    "hematology": [
        "hematology",
        "heme",
        "blood",
        "bleeding",
        "clotting",
        "anemia",
        "transfusion",
        "thrombosis",
        "hematologic",
    ],
    "oncology": [
        "oncology",
        "cancer",
        "tumor",
        "malignancy",
        "leukemia",
        "lymphoma",
    ],
    "endocrinology": [
        "endocrinology",
        "endocrine",
        "diabetes",
        "thyroid",
        "hormone",
        "dka",
        "diabetic",
    ],
    "infectious_disease": [
        "infectious disease",
        "infection",
        "sepsis",
        "bacterial",
        "viral",
        "meningitis",
    ],
    "urology": [
        "urology",
        "urinary",
        "bladder",
        "ureter",
    ],
    "surgery": ["surgery", "surgical", "operative", "post-op", "operation"],
    "trauma": ["trauma", "injury", "accident", "burn", "fracture"],
    "rheumatology": [
        "rheumatology",
        "rheum",
        "kawasaki",
        "autoimmune",
        "arthritis",
        "mis-c",
    ],
    "psychiatric": ["psychiatric", "psych", "mental health", "behavioral", "psychosis"],
    "maternal": ["maternal", "pregnancy", "pregnant", "birth", "obstetric"],
    "transplant": ["transplant", "rejection", "donor", "graft"],
    "ophthalmology": [
        "ophthalmology",
        "eye",
        "ophthalmic",
        "ocular",
        "vision",
        "ophthalmologic",
        "retina",
    ],
    "interventional_radiology": [
        "interventional radiology",
        "ir",
        "catheter",
        "thrombolysis",
    ],
    # Other
    "monitoring": ["monitoring", "telemetry", "continuous", "hourly"],
    "weight_restrictions": ["weight", "kg", "weighing"],
    "transport": ["transport", "transportation", "ambulance", "helicopter", "airlift"],
}

# Condition keywords for extracting medical conditions
CONDITION_KEYWORDS = [
    "active",
    "acute",
    "requiring",
    "with",
    "needing",
    "dependent",
    "on",
    "post",
    "severe",
    "critical",
    "unstable",
]

# Age group mapping
AGE_GROUPS = {
    "adult": ["adult", "adults", "18 years", "18 and older"],
    "pediatric": ["pediatric", "child", "children", "under 18", "<18"],
    "neonate": ["neonate", "newborn", "infant", "<28 days", "less than 28 days"],
}

# Severity levels
SEVERITY_LEVELS = [
    "minimal",
    "mild",
    "moderate",
    "severe",
    "critical",
    "life-threatening",
]

# Exclusion types
EXCLUSION_TYPES = [
    "absolute",  # Patient cannot be admitted under any circumstances
    "relative",  # Patient can be admitted with certain conditions
    "conditional",  # Patient can be admitted if specific criteria are met
]
