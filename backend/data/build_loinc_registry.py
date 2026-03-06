"""
Build LOINC-native BiomarkerRegistry from LOINC 2.81 database.

Filters for ~200-300 commonly ordered lab tests and maps them to
the Telivex registry schema with Indian lab aliases.

Usage:
    python -m data.build_loinc_registry

Output:
    backend/data/BiomarkerRegistry_v2_loinc.csv
"""

import csv
import json
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Paths
LOINC_DIR = Path(os.path.expanduser("~/Downloads/Loinc_2.81"))
LOINC_CSV = LOINC_DIR / "LoincTable" / "Loinc.csv"
CURRENT_REGISTRY = Path(__file__).parent / "BiomarkerRegistry_v1.csv"
OUTPUT_CSV = Path(__file__).parent / "BiomarkerRegistry_v2_loinc.csv"
PANEL_MAP_OUTPUT = Path(__file__).parent / "panel_category_map.json"

# ============================================================================
# LOINC Filters
# ============================================================================
ALLOWED_CLASSES = {"CHEM", "HEM/BC", "COAG", "UA", "SERO", "DRUG/TOX"}
ALLOWED_SYSTEMS = {
    "Ser/Plas",
    "Bld",
    "Urine",
    "Ser/Plas/Bld",
    "Ser",
    "Plas",
    "RBC",
    "WBC",
    "Bld.dot",
    "BldC",
    "BldA",
    "BldV",
    "Ser/Plas^fasting",
    "Urine^24H",
}
ALLOWED_SCALE = {"Qn"}  # Quantitative only
ALLOWED_CLASSTYPE = {"1", "2"}  # Laboratory, Clinical

# ============================================================================
# LOINC CLASS -> Telivex Category Mapping
# ============================================================================
CLASS_TO_CATEGORY = {
    "CHEM": "Chemistry",
    "HEM/BC": "Hematology",
    "COAG": "Coagulation",
    "UA": "Urinalysis",
    "SERO": "Serology",
    "DRUG/TOX": "Toxicology",
}

# ============================================================================
# LOINC PROPERTY -> Readable Name
# ============================================================================
PROPERTY_MAP = {
    "MCnc": "Mass concentration",
    "SCnc": "Substance concentration",
    "MFr": "Mass fraction",
    "NFr": "Number fraction",
    "Naric": "Number areal concentration",
    "NCnc": "Number concentration",
    "ACnc": "Arbitrary concentration",
    "CCnc": "Catalytic concentration",
    "Vel": "Velocity",
    "Time": "Time",
    "Ratio": "Ratio",
    "RelTime": "Relative time",
    "Titr": "Titer",
    "SRat": "Substance rate",
    "MRat": "Mass rate",
    "CRat": "Catalytic rate",
    "EntVol": "Entitic volume",
    "EntMass": "Entitic mass",
    "Visc": "Viscosity",
    "Len": "Length",
    "Pres": "Pressure",
    "Temp": "Temperature",
    "LsCnc": "Log substance concentration",
    "Vol": "Volume",
}

# ============================================================================
# LOINC SYSTEM -> Readable Specimen Name
# ============================================================================
SYSTEM_MAP = {
    "Ser/Plas": "Serum/Plasma",
    "Bld": "Whole Blood",
    "Urine": "Urine",
    "Ser/Plas/Bld": "Serum/Plasma/Blood",
    "Ser": "Serum",
    "Plas": "Plasma",
    "RBC": "Red Blood Cells",
    "WBC": "White Blood Cells",
    "Bld.dot": "Blood spot",
    "BldC": "Capillary Blood",
    "BldA": "Arterial Blood",
    "BldV": "Venous Blood",
    "Ser/Plas^fasting": "Serum/Plasma (Fasting)",
    "Urine^24H": "Urine (24 Hour)",
}

# ============================================================================
# Lab Aliases by LOINC Code
# Keyed by LOINC code to avoid cross-contamination from shared COMPONENT names
# (e.g., LOINC uses "Hemoglobin" as COMPONENT for MCH, MCHC, and actual Hemoglobin)
# ============================================================================
LOINC_ALIASES: dict[str, list[str]] = {
    # CBC
    "718-7": ["Hemoglobin", "Haemoglobin", "Hb", "HGB", "Hgb"],
    "789-8": [
        "RBC",
        "Red Blood Cell Count",
        "RBC Count",
        "Red Blood Cells",
        "Total RBC Count",
        "Erythrocytes",
    ],
    "6690-2": [
        "WBC",
        "White Blood Cell Count",
        "WBC Count",
        "TLC",
        "Total Leucocyte Count",
        "Total Leukocyte Count",
        "White Blood Cells",
        "Leukocytes",
    ],
    "777-3": ["Platelet Count", "PLT", "Platelet", "Platelets", "Thrombocyte Count"],
    "4544-3": ["Hct", "PCV", "Packed Cell Volume", "HCT", "Hematocrit", "Haematocrit"],
    "787-2": ["MCV", "Mean Corpuscular Volume"],
    "785-6": ["MCH", "Mean Corpuscular Hemoglobin", "Mean Corpuscular Haemoglobin"],
    "786-4": ["MCHC", "Mean Corpuscular Hemoglobin Concentration"],
    "788-0": ["RDW", "RDW-CV", "Red Cell Distribution Width"],
    "32623-1": ["MPV", "Mean Platelet Volume"],
    "4537-7": [
        "ESR",
        "Erythrocyte Sedimentation Rate",
        "Sed Rate",
        "ESR - Erythrocyte Sedimentation Rate",
    ],
    "30384-2": ["RDW", "RDW-CV", "Red Cell Distribution Width"],
    # Differential %
    "770-8": ["Neutrophils %", "Neutrophil %", "Neutrophils"],
    "736-9": ["Lymphocytes %", "Lymphocyte %", "Lymphocytes"],
    "5905-5": ["Monocytes %", "Monocyte %", "Monocytes"],
    "713-8": ["Eosinophils %", "Eosinophil %", "Eosinophils"],
    "706-2": ["Basophils %", "Basophil %", "Basophils"],
    # Differential absolute
    "751-8": ["Absolute Neutrophil Count", "ANC", "Neutrophils Absolute"],
    "731-0": ["Absolute Lymphocyte Count", "ALC", "Lymphocytes Absolute"],
    "742-7": ["Absolute Monocyte Count", "AMC", "Monocytes Absolute"],
    "711-2": ["Absolute Eosinophil Count", "AEC", "Eosinophils Absolute"],
    "704-7": ["Absolute Basophil Count", "ABC", "Basophils Absolute"],
    # HbA1c & Diabetes
    "17856-6": [
        "HbA1c",
        "Hba1c",
        "HBA1C",
        "A1C",
        "HgbA1c",
        "Glycated Hemoglobin",
        "Glycated Haemoglobin",
        "Glycosylated Hemoglobin",
        "Glycosylated Haemoglobin",
        "Hemoglobin A1c",
    ],
    "4548-4": [
        "HbA1c",
        "Hba1c",
        "HBA1C",
        "A1C",
        "Glycated Hemoglobin",
        "Glycosylated Hemoglobin",
    ],
    "2345-7": ["Blood Sugar", "Blood Glucose", "Glucose", "RBS", "Random Blood Sugar"],
    "1558-6": [
        "FBS",
        "Fasting Blood Sugar",
        "Fasting Glucose",
        "Fasting Blood Glucose",
        "Fasting Plasma Glucose",
        "FBG",
    ],
    "1521-4": ["PPBS", "Post Prandial Blood Sugar", "Glucose 2hr Post"],
    # Lipids
    "2093-3": [
        "Total Cholesterol",
        "Cholesterol Total",
        "TC",
        "Cholesterol",
        "Cholestrol",
    ],
    "2085-9": [
        "HDL",
        "HDL Cholesterol",
        "HDL-C",
        "High Density Lipoprotein",
        "HDL-Cholesterol",
    ],
    "13457-7": [
        "LDL",
        "LDL Cholesterol",
        "LDL-C",
        "Low Density Lipoprotein",
        "LDL-Cholesterol",
        "LDL Calculated",
    ],
    "2089-1": ["LDL Direct", "LDL Cholesterol Direct"],
    "2571-8": ["Triglycerides", "TG", "Trigs", "Serum Triglycerides", "Triglyceride"],
    "13458-5": ["VLDL", "VLDL Cholesterol", "VLDL-C", "V.L.D.L", "VLDL Calculated"],
    "9830-1": [
        "TC/HDL Ratio",
        "Cholesterol Ratio",
        "Total Cholesterol/HDL Ratio",
        "Chol/HDL Ratio",
    ],
    # Kidney
    "2160-0": ["Creatinine", "S. Creatinine", "Serum Creatinine", "Creat"],
    "3094-0": ["BUN", "Blood Urea Nitrogen", "Urea", "Blood Urea"],
    "3084-1": ["Uric Acid", "Serum Uric Acid", "Urate"],
    "33914-3": ["eGFR", "Estimated GFR", "GFR"],
    # Liver
    "1742-6": [
        "ALT",
        "SGPT",
        "SGPT/ALT",
        "Alanine Transaminase",
        "Alanine Aminotransferase",
        "Serum Glutamic Pyruvic Transaminase",
    ],
    "1920-8": [
        "AST",
        "SGOT",
        "SGOT/AST",
        "Aspartate Transaminase",
        "Aspartate Aminotransferase",
        "Serum Glutamic Oxaloacetic Transaminase",
    ],
    "6768-6": ["ALP", "Alkaline Phosphatase", "Alk Phos"],
    "1975-2": [
        "Total Bilirubin",
        "Bilirubin Total",
        "T. Bilirubin",
        "T.Bil",
        "Serum Bilirubin Total",
    ],
    "1968-7": [
        "Direct Bilirubin",
        "Bilirubin Direct",
        "Conjugated Bilirubin",
        "D. Bilirubin",
        "D.Bil",
        "Serum Bilirubin Direct",
    ],
    "1971-1": [
        "Indirect Bilirubin",
        "Bilirubin Indirect",
        "Unconjugated Bilirubin",
        "Serum Bilirubin Indirect",
    ],
    "2885-2": ["Total Protein", "Serum Total Protein", "TP"],
    "1751-7": ["Albumin", "Serum Albumin", "Alb"],
    "10834-0": ["Globulin", "Serum Globulin", "Globulin Calculated"],
    "2324-2": ["GGT", "GGTP", "Gamma GT", "Gamma Glutamyl Transferase"],
    # Thyroid
    "3016-3": [
        "TSH",
        "Thyroid Stimulating Hormone",
        "TSH Ultrasensitive",
        "Thyroid Stimulating Hormone Ultrasensitive",
    ],
    "3024-7": ["Free T4", "FT4", "Free Thyroxine"],
    "3051-0": ["Free T3", "FT3", "Free Triiodothyronine"],
    "3026-2": ["T4", "Total T4", "Thyroxine", "Thyroxine Total", "Total Thyroxine"],
    "3053-6": [
        "T3",
        "Total T3",
        "Triiodothyronine",
        "Triiodothyronine Total",
        "Total Triiodothyronine",
    ],
    # Electrolytes
    "2951-2": ["Sodium", "Na", "Na+", "Serum Sodium"],
    "2823-3": ["Potassium", "K", "K+", "Serum Potassium"],
    "2075-0": ["Chloride", "Cl", "Cl-", "Serum Chloride"],
    "17861-6": [
        "Calcium",
        "Ca",
        "Ca++",
        "Serum Calcium",
        "Total Calcium",
        "Calcium Serum",
    ],
    "2777-1": ["Phosphorus", "Phosphate", "Inorganic Phosphorus", "Serum Phosphorus"],
    "19123-9": ["Magnesium", "Mg", "Serum Magnesium"],
    # Iron studies
    "2498-4": ["Iron", "Fe", "Serum Iron"],
    "2500-7": ["TIBC", "Total Iron Binding Capacity"],
    "2276-4": ["Ferritin", "Serum Ferritin"],
    "2502-3": ["Transferrin Saturation", "TSAT", "Iron Saturation"],
    # Vitamins
    "2132-9": ["Vitamin B12", "B12", "Vit B12", "Cyanocobalamin"],
    "2284-8": ["Folic Acid", "Folate", "Vitamin B9"],
    "1989-3": [
        "Vitamin D",
        "25-OH Vitamin D",
        "Vit D",
        "Vitamin D3",
        "25-Hydroxy Vitamin D",
        "Vitamin D 25 Hydroxy",
    ],
    # Inflammation
    "1988-5": ["CRP", "C-Reactive Protein"],
    "30522-7": ["hs-CRP", "High Sensitivity CRP", "CRP Highly Sensitive"],
    # Coagulation
    "5902-2": ["PT", "Prothrombin Time"],
    "6301-6": ["INR", "International Normalized Ratio"],
    "3173-2": ["aPTT", "APTT", "Activated Partial Thromboplastin Time", "PTT"],
    "3255-7": ["Fibrinogen"],
    "48065-7": ["D-Dimer", "D Dimer"],
    # Hormones
    "20448-7": ["Insulin", "Fasting Insulin", "Serum Insulin", "Insulin Fasting"],
    "2143-6": ["Cortisol", "Serum Cortisol", "Morning Cortisol"],
    "2842-3": ["Prolactin", "PRL"],
    "2986-8": ["Testosterone", "Total Testosterone", "Serum Testosterone"],
    "2243-4": ["Estradiol", "E2", "Oestradiol"],
    "2839-9": ["Progesterone"],
    "15067-2": ["FSH", "Follicle Stimulating Hormone"],
    "10501-5": ["LH", "Luteinizing Hormone"],
    # Tumor markers
    "2857-1": ["PSA", "Prostate Specific Antigen", "Total PSA"],
    "2039-6": ["CEA", "Carcinoembryonic Antigen"],
    "1834-1": ["AFP", "Alpha Fetoprotein"],
    "21000-5": ["Beta HCG", "HCG", "Pregnancy Test"],
    # Cardiac/Enzymes
    "2532-0": ["LDH", "Lactate Dehydrogenase"],
    "2157-6": ["CK", "CPK", "Creatine Kinase", "Creatine Phosphokinase"],
    # Pancreatic
    "1798-8": ["Amylase", "Serum Amylase"],
    "3040-3": ["Lipase", "Serum Lipase"],
    # Other
    "13965-9": ["Homocysteine", "Serum Homocysteine"],
}

# ============================================================================
# Priority LOINC codes to always include (even if COMMON_TEST_RANK is 0)
# These are commonly ordered in Indian labs
# ============================================================================
PRIORITY_LOINC_CODES = {
    # HbA1c & Diabetes
    "17856-6",  # HbA1c (HPLC)
    "4548-4",  # HbA1c (general)
    "2345-7",  # Glucose
    "1558-6",  # Fasting glucose
    "1521-4",  # Glucose 2hr post
    # Lipids
    "2093-3",  # Cholesterol total
    "2085-9",  # HDL
    "13457-7",  # LDL (calculated)
    "2571-8",  # Triglycerides
    "2089-1",  # LDL (direct)
    "13458-5",  # VLDL (calculated)
    "9830-1",  # TC/HDL ratio
    # Kidney
    "2160-0",  # Creatinine
    "3094-0",  # BUN
    "3084-1",  # Urate/Uric acid
    "33914-3",  # eGFR
    # Liver
    "1742-6",  # ALT
    "1920-8",  # AST
    "6768-6",  # ALP
    "1975-2",  # Bilirubin total
    "1968-7",  # Bilirubin direct
    "1971-1",  # Bilirubin indirect (calculated)
    "2885-2",  # Protein total
    "1751-7",  # Albumin
    "10834-0",  # Globulin (calculated)
    "2324-2",  # GGT
    # CBC
    "718-7",  # Hemoglobin
    "789-8",  # RBC
    "6690-2",  # WBC
    "777-3",  # Platelets
    "4544-3",  # Hematocrit
    "787-2",  # MCV
    "785-6",  # MCH
    "786-4",  # MCHC
    "788-0",  # RDW
    "32623-1",  # MPV
    # Differential
    "770-8",  # Neutrophils %
    "736-9",  # Lymphocytes %
    "5905-5",  # Monocytes %
    "713-8",  # Eosinophils %
    "706-2",  # Basophils %
    "751-8",  # Neutrophils #
    "731-0",  # Lymphocytes #
    "742-7",  # Monocytes #
    "711-2",  # Eosinophils #
    "704-7",  # Basophils #
    "4537-7",  # ESR (Westergren) — 30384-2 is deprecated RDW
    # Thyroid
    "3016-3",  # TSH
    "3024-7",  # Free T4
    "3051-0",  # Free T3
    "3026-2",  # T4 total
    "3053-6",  # T3 total
    # Electrolytes
    "2951-2",  # Sodium
    "2823-3",  # Potassium
    "2075-0",  # Chloride
    "17861-6",  # Calcium
    "2777-1",  # Phosphate
    "19123-9",  # Magnesium
    # Iron studies
    "2498-4",  # Iron
    "2500-7",  # TIBC
    "2276-4",  # Ferritin
    "2502-3",  # Transferrin saturation
    # Vitamins
    "2132-9",  # Vitamin B12
    "2284-8",  # Folate
    "1989-3",  # Vitamin D (25-OH)
    # Inflammation
    "1988-5",  # CRP
    "30522-7",  # hs-CRP
    # Coagulation
    "5902-2",  # PT
    "6301-6",  # INR
    "3173-2",  # aPTT
    "3255-7",  # Fibrinogen
    "48065-7",  # D-dimer (FEU)
    # Hormones
    "20448-7",  # Insulin fasting
    "2143-6",  # Cortisol
    "2842-3",  # Prolactin
    "2986-8",  # Testosterone total
    "2243-4",  # Estradiol
    "2839-9",  # Progesterone
    "15067-2",  # FSH
    "10501-5",  # LH
    # Tumor markers
    "2857-1",  # PSA total
    "2039-6",  # CEA
    "1834-1",  # AFP
    # Cardiac
    "2532-0",  # LDH
    "2157-6",  # CK total
    # Pancreatic
    "1798-8",  # Amylase
    "3040-3",  # Lipase
    # Other common
    "13965-9",  # Homocysteine
    "21000-5",  # HCG quantitative
}

# ============================================================================
# Canonical Unit Overrides
# LOINC EXAMPLE_UNITS often use notation that doesn't match Indian lab reports.
# Override with units the normalizer already handles.
# ============================================================================
CANONICAL_UNIT_OVERRIDES: dict[str, str] = {
    # Enzymes: LOINC "arb U/L" → standardize to "U/L"
    "1742-6": "U/L",  # ALT
    "1920-8": "U/L",  # AST
    "6768-6": "U/L",  # ALP
    "2324-2": "U/L",  # GGT
    "2532-0": "U/L",  # LDH
    "2157-6": "U/L",  # CK
    "1798-8": "U/L",  # Amylase
    "3040-3": "U/L",  # Lipase
    # CBC counts: standardize to SI-adjacent units
    "6690-2": "10*9/L",  # WBC (= 10^3/µL)
    "777-3": "10*9/L",  # Platelets
    "751-8": "10*9/L",  # Neutrophils #
    "731-0": "10*9/L",  # Lymphocytes #
    "742-7": "10*9/L",  # Monocytes #
    "711-2": "10*9/L",  # Eosinophils #
    "704-7": "10*9/L",  # Basophils #
    "789-8": "10*12/L",  # RBC (= 10^6/µL)
    # ESR
    "4537-7": "mm/hr",  # ESR
    # Hemoglobin & red cell indices
    "718-7": "g/dL",  # Hemoglobin
    "4544-3": "%",  # Hematocrit/PCV
    "787-2": "fL",  # MCV
    "785-6": "pg",  # MCH
    "786-4": "g/dL",  # MCHC
    "788-0": "%",  # RDW-CV
    "32623-1": "fL",  # MPV
    # Differential %
    "770-8": "%",
    "736-9": "%",
    "5905-5": "%",
    "713-8": "%",
    "706-2": "%",
    # Chemistry
    "2160-0": "mg/dL",  # Creatinine
    "3094-0": "mg/dL",  # BUN
    "3084-1": "mg/dL",  # Uric acid
    "1975-2": "mg/dL",  # Bilirubin total
    "1968-7": "mg/dL",  # Bilirubin direct
    "1971-1": "mg/dL",  # Bilirubin indirect
    "2885-2": "g/dL",  # Total protein
    "1751-7": "g/dL",  # Albumin
    "10834-0": "g/dL",  # Globulin
    # Lipids
    "2093-3": "mg/dL",
    "2085-9": "mg/dL",
    "13457-7": "mg/dL",
    "2089-1": "mg/dL",
    "2571-8": "mg/dL",
    "13458-5": "mg/dL",
    # Diabetes
    "2345-7": "mg/dL",
    "1558-6": "mg/dL",
    "1521-4": "mg/dL",
    "17856-6": "%",
    "4548-4": "%",
    # Thyroid
    "3016-3": "mIU/L",  # TSH
    "3024-7": "ng/dL",  # Free T4
    "3051-0": "pg/mL",  # Free T3
    "3026-2": "µg/dL",  # Total T4
    "3053-6": "ng/dL",  # Total T3
    # Electrolytes
    "2951-2": "mmol/L",
    "2823-3": "mmol/L",
    "2075-0": "mmol/L",
    "17861-6": "mg/dL",  # Calcium
    "2777-1": "mg/dL",  # Phosphorus
    "19123-9": "mg/dL",  # Magnesium
    # Iron
    "2498-4": "µg/dL",
    "2500-7": "µg/dL",
    "2276-4": "ng/mL",  # Ferritin
    # Vitamins
    "2132-9": "pg/mL",
    "2284-8": "ng/mL",
    "1989-3": "ng/mL",
    # Inflammation
    "1988-5": "mg/dL",
    "30522-7": "mg/L",
    # Hormones
    "20448-7": "µIU/mL",  # Insulin
    "2143-6": "µg/dL",  # Cortisol
    "13965-9": "µmol/L",  # Homocysteine
    # Coagulation
    "5902-2": "seconds",
    "6301-6": "",
    "3173-2": "seconds",
    # Ratios
    "9830-1": "ratio",
}


def load_loinc_data() -> list[dict]:
    """Load and filter LOINC CSV for relevant lab tests."""
    logger.info("Loading LOINC data from %s", LOINC_CSV)

    if not LOINC_CSV.exists():
        raise FileNotFoundError(
            f"LOINC CSV not found at {LOINC_CSV}. "
            "Download from https://loinc.org/downloads/"
        )

    rows = []
    total = 0
    with open(LOINC_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            loinc_num = row["LOINC_NUM"]

            # Always include priority codes
            if loinc_num in PRIORITY_LOINC_CODES:
                rows.append(row)
                continue

            # Filter criteria
            if row["STATUS"] != "ACTIVE":
                continue
            if row["CLASS"] not in ALLOWED_CLASSES:
                continue
            if row["CLASSTYPE"] not in ALLOWED_CLASSTYPE:
                continue
            if row["SCALE_TYP"] not in ALLOWED_SCALE:
                continue
            if row["SYSTEM"] not in ALLOWED_SYSTEMS:
                continue

            # Must have COMMON_TEST_RANK <= 500 (top ~300 most common)
            rank = row.get("COMMON_TEST_RANK", "").strip()
            if not rank or rank == "0":
                continue
            try:
                if int(rank) > 500:
                    continue
            except ValueError:
                continue

            rows.append(row)

    logger.info("Loaded %d total LOINC codes, filtered to %d", total, len(rows))
    return rows


def load_current_registry() -> dict[str, dict]:
    """Load current registry to preserve reference range notes."""
    registry = {}
    if not CURRENT_REGISTRY.exists():
        return registry

    with open(CURRENT_REGISTRY, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Index by analyte_name (lowercased) for fuzzy matching
            name = row["analyte_name"].lower().strip()
            registry[name] = row
    return registry


def build_aliases(row: dict) -> list[str]:
    """Build alias list from LOINC data + Indian lab names.

    IMPORTANT: No RELATEDNAMES2 — too noisy and causes cross-contamination.
    Indian aliases use EXACT component match only.
    """
    aliases = set()

    # LOINC names (curated fields only, no RELATEDNAMES2)
    if row.get("SHORTNAME"):
        aliases.add(row["SHORTNAME"])
    if row.get("CONSUMER_NAME"):
        aliases.add(row["CONSUMER_NAME"])
    if row.get("LONG_COMMON_NAME"):
        aliases.add(row["LONG_COMMON_NAME"])
    if row.get("DisplayName"):
        aliases.add(row["DisplayName"])

    # Lab aliases keyed by LOINC code (avoids component name collisions)
    loinc_num = row.get("LOINC_NUM", "")
    if loinc_num in LOINC_ALIASES:
        aliases.update(LOINC_ALIASES[loinc_num])

    # Remove the analyte_name itself to avoid duplication
    long_name = row.get("LONG_COMMON_NAME", "")
    aliases.discard(long_name)

    return sorted(aliases)


def map_to_telivex_schema(loinc_rows: list[dict]) -> list[dict]:
    """Map filtered LOINC rows to Telivex registry schema."""
    current = load_current_registry()
    results = []
    seen_loinc = set()

    for row in loinc_rows:
        loinc_num = row["LOINC_NUM"]

        # Skip duplicates
        if loinc_num in seen_loinc:
            continue
        seen_loinc.add(loinc_num)

        component = row.get("COMPONENT", "")
        system = row.get("SYSTEM", "")
        prop = row.get("PROPERTY", "")
        loinc_class = row.get("CLASS", "")
        long_name = row.get("LONG_COMMON_NAME", "") or row.get(
            "CONSUMER_NAME", component
        )
        example_units = row.get("EXAMPLE_UNITS", "").strip()

        # Map fields
        specimen = SYSTEM_MAP.get(system, system)
        measurement_property = PROPERTY_MAP.get(prop, prop)
        category = CLASS_TO_CATEGORY.get(loinc_class, loinc_class)

        # Canonical unit: prefer override, fall back to EXAMPLE_UNITS
        if loinc_num in CANONICAL_UNIT_OVERRIDES:
            canonical_unit = CANONICAL_UNIT_OVERRIDES[loinc_num]
        elif example_units:
            # Clean up LOINC EXAMPLE_UNITS (may contain semicolons)
            canonical_unit = example_units.split(";")[0].strip()
        else:
            canonical_unit = ""

        # Build aliases
        aliases = build_aliases(row)

        # Check if we have reference range notes from current registry
        ref_notes = ""
        for name_key, old_row in current.items():
            if any(a.lower() == name_key for a in aliases):
                ref_notes = old_row.get("default_reference_range_notes", "")
                break

        # Determine panel_seed from class/component
        panel_seed = _derive_panel_seed(component, loinc_class, system)

        results.append(
            {
                "biomarker_id": loinc_num,
                "analyte_name": long_name,
                "specimen": specimen,
                "measurement_property": measurement_property,
                "canonical_unit": canonical_unit,
                "category": category,
                "panel_seed": panel_seed,
                "is_derived": str(bool(row.get("FORMULA", "").strip())),
                "aliases": json.dumps(aliases),
                "loinc_code": loinc_num,
                "loinc_component": component,
                "default_reference_range_notes": ref_notes,
            }
        )

    return results


def _derive_panel_seed(component: str, loinc_class: str, system: str) -> str:
    """Derive a panel_seed from LOINC component and class."""
    comp_lower = component.lower()

    # CBC / Hematology
    if any(
        term in comp_lower
        for term in [
            "hemoglobin",
            "erythrocyte",
            "hematocrit",
            "leukocyte",
            "platelet",
            "neutrophil",
            "lymphocyte",
            "monocyte",
            "eosinophil",
            "basophil",
            "reticulocyte",
        ]
    ):
        if "a1c" in comp_lower:
            return "HbA1c Panel"
        return "Complete Blood Count"

    # ESR
    if "sedimentation" in comp_lower:
        return "Complete Blood Count"

    # Lipids
    if any(
        term in comp_lower
        for term in [
            "cholesterol",
            "triglyceride",
            "lipoprotein",
        ]
    ):
        return "Lipid Profile"

    # Liver
    if (
        any(
            term in comp_lower
            for term in [
                "aminotransferase",
                "bilirubin",
                "alkaline phosphatase",
                "gamma glutamyl",
                "albumin",
                "protein",
            ]
        )
        and "urine" not in system.lower()
    ):
        return "Liver Function Test"

    # Kidney
    if (
        any(
            term in comp_lower
            for term in [
                "creatinine",
                "urea",
                "urate",
                "glomerular",
            ]
        )
        and "urine" not in system.lower()
    ):
        return "Kidney Function Test"

    # Thyroid
    if any(
        term in comp_lower
        for term in [
            "thyrotropin",
            "thyroxine",
            "triiodothyronine",
        ]
    ):
        return "Thyroid Profile"

    # Electrolytes
    if any(
        term in comp_lower
        for term in [
            "sodium",
            "potassium",
            "chloride",
            "calcium",
            "phosphate",
            "magnesium",
            "bicarbonate",
        ]
    ):
        return "Electrolytes"

    # Iron studies
    if any(
        term in comp_lower
        for term in [
            "iron",
            "ferritin",
            "transferrin",
        ]
    ):
        return "Iron Studies"

    # Vitamins
    if any(
        term in comp_lower
        for term in [
            "cobalamin",
            "folate",
            "vitamin",
            "hydroxyvitamin",
        ]
    ):
        return "Vitamins"

    # Diabetes
    if any(term in comp_lower for term in ["glucose", "insulin"]):
        return "Diabetes Panel"

    # Coagulation
    if (
        any(
            term in comp_lower
            for term in [
                "coagulation",
                "fibrinogen",
                "d-dimer",
                "inr",
            ]
        )
        or loinc_class == "COAG"
    ):
        return "Coagulation"

    # Inflammation
    if "reactive protein" in comp_lower:
        return "Inflammatory Markers"

    # Hormones
    if any(
        term in comp_lower
        for term in [
            "testosterone",
            "estradiol",
            "progesterone",
            "cortisol",
            "prolactin",
            "follitropin",
            "lutropin",
            "choriogonadotropin",
        ]
    ):
        return "Hormones"

    # Tumor markers
    if any(
        term in comp_lower
        for term in [
            "prostate specific",
            "carcinoembryonic",
            "fetoprotein",
        ]
    ):
        return "Tumor Markers"

    # Cardiac
    if any(
        term in comp_lower
        for term in [
            "troponin",
            "creatine kinase",
            "lactate dehydrogenase",
            "brain natriuretic",
        ]
    ):
        return "Cardiac Markers"

    # Pancreatic
    if any(term in comp_lower for term in ["amylase", "lipase"]):
        return "Pancreatic Enzymes"

    # Urinalysis
    if "urine" in system.lower() or loinc_class == "UA":
        return "Urinalysis"

    return "Other"


def build_panel_category_map(registry_rows: list[dict]) -> dict:
    """Build panel_seed -> category mapping from the generated registry."""
    panel_map = {}
    for row in registry_rows:
        seed = row["panel_seed"]
        cat = row["category"]
        if seed not in panel_map:
            panel_map[seed] = cat
    return dict(sorted(panel_map.items()))


def write_output(rows: list[dict]) -> None:
    """Write the registry CSV."""
    fieldnames = [
        "biomarker_id",
        "analyte_name",
        "specimen",
        "measurement_property",
        "canonical_unit",
        "category",
        "panel_seed",
        "is_derived",
        "aliases",
        "loinc_code",
        "loinc_component",
        "default_reference_range_notes",
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Written %d biomarkers to %s", len(rows), OUTPUT_CSV)


def print_summary(rows: list[dict]) -> None:
    """Print a summary of the generated registry."""
    print("\n" + "=" * 60)
    print("LOINC Registry Build Summary")
    print("=" * 60)
    print(f"Total biomarkers: {len(rows)}")

    # By category
    categories = {}
    for row in rows:
        cat = row["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print("\nBy Category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # By panel_seed
    panels = {}
    for row in rows:
        seed = row["panel_seed"]
        panels[seed] = panels.get(seed, 0) + 1

    print("\nBy Panel:")
    for panel, count in sorted(panels.items(), key=lambda x: -x[1]):
        print(f"  {panel}: {count}")

    # Priority codes coverage
    found = {r["biomarker_id"] for r in rows}
    missing_priority = PRIORITY_LOINC_CODES - found
    print(f"\nPriority LOINC codes: {len(PRIORITY_LOINC_CODES)}")
    print(f"  Found: {len(PRIORITY_LOINC_CODES - missing_priority)}")
    if missing_priority:
        print(f"  Missing: {len(missing_priority)}")
        for code in sorted(missing_priority):
            print(f"    - {code}")

    print("=" * 60)


def main():
    # Step 1: Load and filter LOINC
    loinc_rows = load_loinc_data()

    # Step 2: Map to Telivex schema
    registry = map_to_telivex_schema(loinc_rows)

    # Step 3: Write output
    write_output(registry)

    # Step 4: Build and write panel category map
    panel_map = build_panel_category_map(registry)
    with open(PANEL_MAP_OUTPUT, "w") as f:
        json.dump(panel_map, f, indent=2)
    logger.info("Written panel category map to %s", PANEL_MAP_OUTPUT)

    # Step 5: Summary
    print_summary(registry)


if __name__ == "__main__":
    main()
