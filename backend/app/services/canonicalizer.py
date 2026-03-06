"""
Canonicalization service - matches raw labels to biomarker registry.

Key principle: NEVER invent biomarker_ids. If no match found, surface as unmapped.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BiomarkerRegistry


# Load panel → category mapping (deterministic, no ML)
_PANEL_CATEGORY_MAP_PATH = (
    Path(__file__).parent.parent.parent / "data" / "panel_category_map.json"
)
_PANEL_CATEGORY_MAP: dict[str, str] = {}


def _load_panel_category_map() -> dict[str, str]:
    """Load the panel_seed → category mapping from JSON file."""
    global _PANEL_CATEGORY_MAP
    if not _PANEL_CATEGORY_MAP:
        try:
            with open(_PANEL_CATEGORY_MAP_PATH, "r") as f:
                data = json.load(f)
                _PANEL_CATEGORY_MAP = data.get("mapping", {})
        except (FileNotFoundError, json.JSONDecodeError):
            _PANEL_CATEGORY_MAP = {}
    return _PANEL_CATEGORY_MAP


def get_category_for_panel(panel_seed: Optional[str]) -> Optional[str]:
    """Get category for a panel_seed.

    Uses the panel_seed directly as the display category since it provides
    meaningful grouping (e.g., "Complete Blood Count", "Lipid Profile").
    """
    return panel_seed or None


@dataclass
class CanonicalMatch:
    """Result of canonicalization attempt."""

    biomarker_id: str
    analyte_name: str
    canonical_unit: str
    confidence: float  # 1.0 = exact match, lower for fuzzy
    category: Optional[str] = None  # Derived from panel_seed → category mapping
    panel_seed: Optional[str] = None  # Original panel_seed from registry


@dataclass
class CanonicalResult:
    """Result of attempting to canonicalize a label."""

    matched: bool
    match: Optional[CanonicalMatch]
    raw_label: str
    section: Optional[str] = None  # Section context used for matching


class Canonicalizer:
    """
    Matches raw extracted labels to the authoritative BiomarkerRegistry.

    Rules:
    - Matching is deterministic (no ML/probabilistic methods)
    - Exact alias match → confidence 1.0
    - Normalized match (case, whitespace) → confidence 0.95
    - No match → return unmatched, never guess
    """

    # Method descriptors to strip from labels (often appended in lab reports)
    METHOD_DESCRIPTORS = [
        "colorimetric",
        "calculated",
        "electrical impedance",
        "flow cytometry",
        "photometry",
        "enzymatic",
        "immunoturbidimetric",
        "turbidimetric",
        "nephelometric",
        "ion selective electrode",
        "double indicator",
        "ion exchange",
        "spectrophotometry",
        "kinetic",
        "reflotron",
        "automated",
        "manual",
    ]

    # British to American spelling mappings
    SPELLING_VARIANTS = {
        "haemoglobin": "hemoglobin",
        "haematocrit": "hematocrit",
        "haemogram": "hemogram",
        "colour": "color",
        "foetal": "fetal",
        "oestrogen": "estrogen",
        "leucocyte": "leukocyte",
        "anaemia": "anemia",
        "diarrhoea": "diarrhea",
        "oedema": "edema",
        "tumour": "tumor",
        "behaviour": "behavior",
        "favour": "favor",
        "honour": "honor",
        "labour": "labor",
        "neighbour": "neighbor",
        "analyse": "analyze",
        "catalyse": "catalyze",
    }

    # Panel/section synonyms - these are equivalent
    PANEL_SYNONYMS = {
        # CBC/Hematogram synonyms
        "complete hemogram": "complete blood count",
        "complete haemogram": "complete blood count",
        "hemogram": "complete blood count",
        "haemogram": "complete blood count",
        "cbc": "complete blood count",
        "full blood count": "complete blood count",
        "fbc": "complete blood count",
        "blood count": "complete blood count",
        # Lipid panel synonyms
        "lipid panel": "lipid profile",
        "lipids": "lipid profile",
        # Liver function
        "lft": "liver function test",
        "liver panel": "liver function test",
        # Kidney function
        "kft": "kidney function test",
        "renal function test": "kidney function test",
        "renal panel": "kidney function test",
        "rft": "kidney function test",
    }

    # Direct label → LOINC code mapping for common lab report labels
    # Used as fallback when alias map lookup fails
    LABEL_TO_LOINC: dict[str, str] = {
        # CBC
        "hemoglobin": "718-7",
        "haemoglobin": "718-7",
        "hb": "718-7",
        "hgb": "718-7",
        "rbc count": "789-8",
        "rbc": "789-8",
        "red blood cell count": "789-8",
        "wbc count": "6690-2",
        "wbc": "6690-2",
        "tlc": "6690-2",
        "total wbc count": "6690-2",
        "total leucocyte count": "6690-2",
        "total leukocyte count": "6690-2",
        "white blood cell count": "6690-2",
        "platelet count": "777-3",
        "platelets": "777-3",
        "pcv": "4544-3",
        "packed cell volume": "4544-3",
        "hematocrit": "4544-3",
        "hct": "4544-3",
        "mcv": "787-2",
        "mean corpuscular volume": "787-2",
        "mch": "785-6",
        "mean corpuscular hemoglobin": "785-6",
        "mchc": "786-4",
        "mean corpuscular hemoglobin concentration": "786-4",
        "rdw": "788-0",
        "rdw cv": "788-0",
        "red cell distribution width": "788-0",
        "mpv": "32623-1",
        "mean platelet volume": "32623-1",
        "esr": "4537-7",
        "esr erythrocyte sedimentation rate": "4537-7",
        "erythrocyte sedimentation rate": "4537-7",
        # Differential %
        "neutrophils": "770-8",
        "lymphocytes": "736-9",
        "monocytes": "5905-5",
        "eosinophils": "713-8",
        "basophils": "706-2",
        # HbA1c & Diabetes
        "hba1c": "17856-6",
        "hemoglobin a1c": "17856-6",
        "glycosylated hemoglobin": "17856-6",
        "glycosylated haemoglobin": "17856-6",
        "glycated hemoglobin": "17856-6",
        "a1c": "17856-6",
        "glucose fasting": "1558-6",
        "fasting glucose": "1558-6",
        "fasting blood sugar": "1558-6",
        "fasting plasma glucose": "1558-6",
        "fbs": "1558-6",
        "blood sugar fasting": "1558-6",
        "glucose": "2345-7",
        "blood sugar": "2345-7",
        "blood glucose": "2345-7",
        # Lipids
        "total cholesterol": "2093-3",
        "cholesterol total": "2093-3",
        "cholesterol": "2093-3",
        "hdl cholesterol": "2085-9",
        "hdl": "2085-9",
        "hdl c": "2085-9",
        "ldl cholesterol": "13457-7",
        "ldl": "13457-7",
        "ldl c": "13457-7",
        "ldl calculated": "13457-7",
        "triglycerides": "2571-8",
        "triglyceride": "2571-8",
        "vldl cholesterol": "13458-5",
        "vldl": "13458-5",
        "v l d l cholesterol": "13458-5",
        "non hdl cholesterol": "43396-1",
        "chol/hdl ratio": "9830-1",
        "total cholesterol/hdl ratio": "9830-1",
        "tc/hdl ratio": "9830-1",
        "cholesterol ratio": "9830-1",
        # Kidney
        "creatinine": "2160-0",
        "serum creatinine": "2160-0",
        "creatinine urine": "2161-8",
        "urine creatinine": "2161-8",
        "urea": "6299-2",
        "blood urea": "6299-2",
        "bun": "3094-0",
        "blood urea nitrogen": "3094-0",
        "blood urea nitrogen bun": "3094-0",
        "uric acid": "3084-1",
        "serum uric acid": "3084-1",
        "egfr": "33914-3",
        "egfr ckd epi": "33914-3",
        "estimated gfr": "33914-3",
        # Liver
        "sgot": "1920-8",
        "sgot/ast": "1920-8",
        "ast": "1920-8",
        "aspartate aminotransferase": "1920-8",
        "sgpt": "1742-6",
        "sgpt/alt": "1742-6",
        "alt": "1742-6",
        "alanine aminotransferase": "1742-6",
        "alp": "6768-6",
        "alkaline phosphatase": "6768-6",
        "total bilirubin": "1975-2",
        "bilirubin total": "1975-2",
        "direct bilirubin": "1968-7",
        "bilirubin direct": "1968-7",
        "indirect bilirubin": "1971-1",
        "bilirubin indirect": "1971-1",
        "total protein": "2885-2",
        "serum total protein": "2885-2",
        "albumin": "1751-7",
        "serum albumin": "1751-7",
        "globulin": "10834-0",
        "serum globulin": "10834-0",
        "ggt": "2324-2",
        "gamma glutamyl transferase": "2324-2",
        # Thyroid
        "tsh": "3016-3",
        "thyroid stimulating hormone": "3016-3",
        "tsh ultrasensitive": "3016-3",
        "thyroid stimulating hormone ultrasensitive": "3016-3",
        "free t4": "3024-7",
        "ft4": "3024-7",
        "free t3": "3051-0",
        "ft3": "3051-0",
        "t4": "3026-2",
        "total thyroxine": "3026-2",
        "thyroxine": "3026-2",
        "t3": "3053-6",
        "total triiodothyronine": "3053-6",
        "triiodothyronine": "3053-6",
        # Electrolytes
        "sodium": "2951-2",
        "serum sodium": "2951-2",
        "potassium": "2823-3",
        "serum potassium": "2823-3",
        "chloride": "2075-0",
        "serum chloride": "2075-0",
        "calcium": "17861-6",
        "calcium serum": "17861-6",
        "serum calcium": "17861-6",
        "phosphorus": "2777-1",
        "serum phosphorus": "2777-1",
        "magnesium": "19123-9",
        "magnesium serum": "19123-9",
        # Iron
        "iron": "2498-4",
        "serum iron": "2498-4",
        "ferritin": "2276-4",
        "serum ferritin": "2276-4",
        "tibc": "2500-7",
        # Vitamins
        "vitamin b12": "2132-9",
        "vitamin b 12": "2132-9",
        "cyanocobalamin": "2132-9",
        "b12": "2132-9",
        "folic acid": "2284-8",
        "folate": "2284-8",
        "vitamin d": "1989-3",
        "vitamin d 25 hydroxy": "1989-3",
        "25 oh vitamin d": "1989-3",
        "25 hydroxy vitamin d": "1989-3",
        "vitamin d 25 oh vitamin d": "1989-3",
        # Inflammation
        "crp": "1988-5",
        "c reactive protein": "1988-5",
        "hs crp": "30522-7",
        # Hormones
        "insulin": "20448-7",
        "insulin fasting": "20448-7",
        "fasting insulin": "20448-7",
        "cortisol": "2143-6",
        "homocysteine": "13965-9",
        # Pancreatic
        "amylase": "1798-8",
        "lipase": "3040-3",
    }

    # Common abbreviation expansions
    ABBREVIATIONS = {
        "hb": "hemoglobin",
        "hgb": "hemoglobin",
        "rbc": "red blood cell",
        "wbc": "white blood cell",
        "plt": "platelet",
        "mcv": "mean corpuscular volume",
        "mch": "mean corpuscular hemoglobin",
        "mchc": "mean corpuscular hemoglobin concentration",
        "rdw": "red cell distribution width",
        "pcv": "packed cell volume",
        "esr": "erythrocyte sedimentation rate",
        "crp": "c-reactive protein",
        "ldl": "low density lipoprotein",
        "hdl": "high density lipoprotein",
        "vldl": "very low density lipoprotein",
        "tsh": "thyroid stimulating hormone",
        "t3": "triiodothyronine",
        "t4": "thyroxine",
        "ft3": "free triiodothyronine",
        "ft4": "free thyroxine",
        "alt": "alanine aminotransferase",
        "ast": "aspartate aminotransferase",
        "alp": "alkaline phosphatase",
        "ggt": "gamma glutamyl transferase",
        "bun": "blood urea nitrogen",
        "egfr": "estimated glomerular filtration rate",
        "hba1c": "glycated hemoglobin",
        "psa": "prostate specific antigen",
        "bnp": "brain natriuretic peptide",
        "ck": "creatine kinase",
        "ldh": "lactate dehydrogenase",
        "mpv": "mean platelet volume",
        "pdw": "platelet distribution width",
    }

    def __init__(self, db: Session):
        self.db = db
        self._alias_map: dict[str, BiomarkerRegistry] = {}
        self._id_map: dict[str, BiomarkerRegistry] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load biomarker registry and build alias lookup map."""
        stmt = select(BiomarkerRegistry)
        biomarkers = self.db.scalars(stmt).all()

        for biomarker in biomarkers:
            # Index by biomarker_id (LOINC code) for direct lookup
            self._id_map[biomarker.biomarker_id] = biomarker

            # Add canonical name
            normalized = self._normalize(biomarker.analyte_name)
            self._alias_map[normalized] = biomarker

            # Add aliases
            if biomarker.aliases:
                for alias in biomarker.aliases:
                    normalized_alias = self._normalize(alias)
                    if normalized_alias:
                        # Don't overwrite existing entries (first-come wins)
                        if normalized_alias not in self._alias_map:
                            self._alias_map[normalized_alias] = biomarker

    # Parenthetical terms to preserve (important for disambiguation)
    PRESERVE_PARENS = {
        "total",
        "direct",
        "indirect",
        "fasting",
        "random",
        "ultrasensitive",
        "calculated",
        "serum",
        "plasma",
        "urine",
        "whole blood",
        "differential",
        "absolute",
        "cv",
        "sd",
    }

    def _normalize(self, text: str) -> str:
        """Normalize text for matching: lowercase, strip whitespace, remove special chars."""
        if not text:
            return ""
        # Lowercase
        result = text.lower().strip()
        # Replace newlines with spaces
        result = result.replace("\n", " ").replace("\r", " ")
        # Normalize whitespace around punctuation (e.g., "Albumin :Globulin" → "albumin:globulin")
        result = re.sub(r"\s*:\s*", ":", result)
        result = re.sub(r"\s*/\s*", "/", result)
        result = re.sub(r"\s*-\s*", " ", result)  # Hyphens to spaces
        result = re.sub(r"\s*,\s*", " ", result)  # Commas to spaces
        # Remove extra whitespace
        result = re.sub(r"\s+", " ", result)

        # Handle parentheses: keep important terms, remove the rest
        def replace_parens(match):
            content = match.group(1).lower().strip()
            # Keep if it's an important term
            for term in self.PRESERVE_PARENS:
                if term in content:
                    return " " + content + " "
            return " "

        result = re.sub(r"\s*\(([^)]*)\)\s*", replace_parens, result)

        # Remove extra whitespace again
        result = re.sub(r"\s+", " ", result)
        # Remove trailing asterisks and flags
        result = re.sub(r"\s*\*+\s*$", "", result)

        # Clean dots from abbreviations (V.L.D.L → vldl)
        # Handle patterns like "v.l.d.l cholesterol" → "vldl cholesterol"
        def clean_dotted_abbrev(match):
            abbrev = match.group(0).replace(".", "")
            return abbrev

        result = re.sub(r"\b([a-z]\.)+[a-z]\b", clean_dotted_abbrev, result)
        return result.strip()

    def _strip_method_descriptors(self, text: str) -> str:
        """Remove method descriptors from label."""
        result = text.lower()
        for method in self.METHOD_DESCRIPTORS:
            # Remove method as standalone word or after newline/space
            result = re.sub(rf"\b{method}\b", "", result, flags=re.IGNORECASE)
        return result.strip()

    def _normalize_spelling(self, text: str) -> str:
        """Normalize British to American spelling."""
        result = text.lower()
        for british, american in self.SPELLING_VARIANTS.items():
            result = result.replace(british, american)
        return result

    def _expand_abbreviation(self, text: str) -> str:
        """Expand common abbreviations."""
        # Only expand if the text is primarily an abbreviation
        words = text.lower().split()
        if len(words) <= 2:
            for word in words:
                clean_word = re.sub(r"[^a-z0-9]", "", word)
                if clean_word in self.ABBREVIATIONS:
                    return self.ABBREVIATIONS[clean_word]
        return text

    # Section keywords that indicate differential (percentage) counts
    DIFFERENTIAL_INDICATORS = [
        "differential",
        "differential leucocyte",
        "differential leukocyte",
        "dlc",
        "percentage",
    ]

    # Section keywords that indicate absolute counts
    ABSOLUTE_INDICATORS = [
        "absolute",
        "absolute leucocyte",
        "absolute leukocyte",
        "alc",
        "count",
    ]

    def _normalize_section(self, section: Optional[str]) -> Optional[str]:
        """Normalize section name using panel synonyms."""
        if not section:
            return None

        section_lower = section.lower().strip()

        # Apply spelling variants first
        for british, american in self.SPELLING_VARIANTS.items():
            section_lower = section_lower.replace(british, american)

        # Check for panel synonyms
        for synonym, canonical in self.PANEL_SYNONYMS.items():
            if synonym in section_lower:
                return canonical

        return section_lower

    def _get_section_qualifier(self, section: Optional[str]) -> Optional[str]:
        """
        Determine if section indicates differential or absolute count.

        Returns 'differential', 'absolute', or None.
        """
        if not section:
            return None

        section_lower = section.lower()

        # Normalize British spellings
        for british, american in self.SPELLING_VARIANTS.items():
            section_lower = section_lower.replace(british, american)

        for indicator in self.DIFFERENTIAL_INDICATORS:
            if indicator in section_lower:
                return "differential"

        for indicator in self.ABSOLUTE_INDICATORS:
            if indicator in section_lower:
                return "absolute"

        return None

    def _build_section_aware_labels(
        self, label: str, section: Optional[str]
    ) -> list[tuple[str, float]]:
        """
        Build labels that incorporate section context.

        For a label like "Neutrophils" in section "Differential Leucocyte Count":
        - "neutrophils differential"
        - "neutrophils differential pct"
        - "differential neutrophils"

        Returns list of (label, confidence) tuples.
        """
        results = []
        qualifier = self._get_section_qualifier(section)

        if not qualifier:
            return results

        normalized = self._normalize(label)

        # Common patterns for differential vs absolute
        if qualifier == "differential":
            results.extend(
                [
                    (f"{normalized} differential", 0.98),
                    (f"{normalized} differential pct", 0.97),
                    (f"{normalized} percent", 0.96),
                    (f"differential {normalized}", 0.95),
                    (f"{normalized} pct", 0.94),
                ]
            )
        elif qualifier == "absolute":
            results.extend(
                [
                    (f"{normalized} absolute", 0.98),
                    (f"{normalized} absolute count", 0.97),
                    (f"absolute {normalized}", 0.96),
                    (f"absolute {normalized} count", 0.95),
                    (f"{normalized} count", 0.94),
                ]
            )

        return results

    def canonicalize(
        self, raw_label: str, section: Optional[str] = None
    ) -> CanonicalResult:
        """
        Attempt to match a raw label to the biomarker registry.

        Args:
            raw_label: The test name from the lab report
            section: Optional section context (e.g., "Differential Leucocyte Count")

        Returns:
            CanonicalResult with match info or unmatched status
        """
        if not raw_label or not raw_label.strip():
            return CanonicalResult(
                matched=False, match=None, raw_label=raw_label, section=section
            )

        # Try progressively more aggressive normalization
        attempts = []

        # 0. Section-aware labels first (highest priority for disambiguation)
        # Check these BEFORE LABEL_TO_LOINC to avoid short-circuiting
        # e.g., "Neutrophils" in "Absolute" section should match 751-8, not 770-8
        section_labels = self._build_section_aware_labels(raw_label, section)
        for attempt, confidence in section_labels:
            if attempt in self._alias_map:
                biomarker = self._alias_map[attempt]
                category = get_category_for_panel(biomarker.panel_seed)
                return CanonicalResult(
                    matched=True,
                    match=CanonicalMatch(
                        biomarker_id=biomarker.biomarker_id,
                        analyte_name=biomarker.analyte_name,
                        canonical_unit=biomarker.canonical_unit,
                        confidence=confidence,
                        category=category,
                        panel_seed=biomarker.panel_seed,
                    ),
                    raw_label=raw_label,
                    section=section,
                )

        # 1. Basic normalization
        normalized = self._normalize(raw_label)
        attempts.append((normalized, 1.0))

        # 1.5. Check LABEL_TO_LOINC for direct LOINC code lookup
        if normalized in self.LABEL_TO_LOINC:
            loinc_code = self.LABEL_TO_LOINC[normalized]
            if loinc_code in self._id_map:
                biomarker = self._id_map[loinc_code]
                category = get_category_for_panel(biomarker.panel_seed)
                return CanonicalResult(
                    matched=True,
                    match=CanonicalMatch(
                        biomarker_id=biomarker.biomarker_id,
                        analyte_name=biomarker.analyte_name,
                        canonical_unit=biomarker.canonical_unit,
                        confidence=0.98,
                        category=category,
                        panel_seed=biomarker.panel_seed,
                    ),
                    raw_label=raw_label,
                    section=section,
                )

        # 1.6. Try parenthesized abbreviation (e.g., "Mean Corp Volume (MCV)" → "mcv")
        paren_match = re.search(r"\(([A-Z]{2,}[A-Z0-9/]*)\)", raw_label)
        if paren_match:
            abbrev = paren_match.group(1).lower()
            if abbrev in self.LABEL_TO_LOINC:
                loinc_code = self.LABEL_TO_LOINC[abbrev]
                if loinc_code in self._id_map:
                    biomarker = self._id_map[loinc_code]
                    category = get_category_for_panel(biomarker.panel_seed)
                    return CanonicalResult(
                        matched=True,
                        match=CanonicalMatch(
                            biomarker_id=biomarker.biomarker_id,
                            analyte_name=biomarker.analyte_name,
                            canonical_unit=biomarker.canonical_unit,
                            confidence=0.97,
                            category=category,
                            panel_seed=biomarker.panel_seed,
                        ),
                        raw_label=raw_label,
                        section=section,
                    )
            # Also try in alias map
            if abbrev in self._alias_map:
                biomarker = self._alias_map[abbrev]
                category = get_category_for_panel(biomarker.panel_seed)
                return CanonicalResult(
                    matched=True,
                    match=CanonicalMatch(
                        biomarker_id=biomarker.biomarker_id,
                        analyte_name=biomarker.analyte_name,
                        canonical_unit=biomarker.canonical_unit,
                        confidence=0.97,
                        category=category,
                        panel_seed=biomarker.panel_seed,
                    ),
                    raw_label=raw_label,
                    section=section,
                )

        # 2. Strip method descriptors
        stripped = self._normalize(self._strip_method_descriptors(raw_label))
        if stripped and stripped != normalized:
            attempts.append((stripped, 0.95))

        # 3. Normalize spelling (British → American)
        american = self._normalize_spelling(stripped or normalized)
        if american and american != stripped:
            attempts.append((american, 0.93))

        # 4. Try abbreviation expansion
        expanded = self._expand_abbreviation(stripped or normalized)
        if expanded and expanded != stripped:
            attempts.append((self._normalize(expanded), 0.90))

        # 5. Generate additional variants
        for base, base_conf in list(attempts):
            for variant in self._generate_variants(base):
                if variant not in [a[0] for a in attempts]:
                    attempts.append((variant, base_conf * 0.95))

        # Try each attempt
        for attempt, confidence in attempts:
            if attempt in self._alias_map:
                biomarker = self._alias_map[attempt]
                category = get_category_for_panel(biomarker.panel_seed)
                return CanonicalResult(
                    matched=True,
                    match=CanonicalMatch(
                        biomarker_id=biomarker.biomarker_id,
                        analyte_name=biomarker.analyte_name,
                        canonical_unit=biomarker.canonical_unit,
                        confidence=confidence,
                        category=category,
                        panel_seed=biomarker.panel_seed,
                    ),
                    raw_label=raw_label,
                    section=section,
                )

        # No match found - do NOT guess
        return CanonicalResult(
            matched=False, match=None, raw_label=raw_label, section=section
        )

    def _generate_variants(self, normalized: str) -> list[str]:
        """Generate variants of the label to try matching."""
        variants = []

        # Remove common prefixes
        prefixes = ["serum ", "plasma ", "blood ", "urine ", "whole blood "]
        for prefix in prefixes:
            if normalized.startswith(prefix):
                variants.append(normalized[len(prefix) :])

        # Remove common suffixes
        suffixes = [" level", " levels", " count", " test", " assay", " value"]
        for suffix in suffixes:
            if normalized.endswith(suffix):
                variants.append(normalized[: -len(suffix)])

        # Try without special characters
        no_special = re.sub(r"[^a-z0-9\s]", "", normalized)
        if no_special != normalized:
            variants.append(no_special)

        # Try extracting just the main term (first word or words before special chars)
        main_term = normalized.split()[0] if normalized.split() else ""
        if main_term and len(main_term) > 2 and main_term != normalized:
            variants.append(main_term)

        return variants

    def refresh(self) -> None:
        """Reload the registry (call after registry updates)."""
        self._alias_map.clear()
        self._id_map.clear()
        self._load_registry()
