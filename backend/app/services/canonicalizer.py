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
_PANEL_CATEGORY_MAP_PATH = Path(__file__).parent.parent.parent / "data" / "panel_category_map.json"
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
    """Get category for a panel_seed using deterministic mapping."""
    if not panel_seed:
        return None
    mapping = _load_panel_category_map()
    return mapping.get(panel_seed)


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

    # Label synonyms - map common lab report labels to registry names
    # These are checked BEFORE alias lookup
    LABEL_SYNONYMS = {
        # Glucose
        "glucose fasting": "fbs",
        "fasting glucose": "fbs",
        "fasting blood sugar": "fbs",
        "fasting plasma glucose": "fbs",
        "blood sugar fasting": "fbs",
        # HbA1c
        "glycosylated hemoglobin": "hba1c",
        "glycosylated haemoglobin": "hba1c",
        "glycated hemoglobin": "hba1c",
        "hba1c": "hba1c",
        "hemoglobin a1c": "hba1c",
        # Liver - Bilirubin
        "bilirubin total": "serum bilirubin total",
        "total bilirubin": "serum bilirubin total",
        "bilirubin direct": "serum bilirubin direct",
        "direct bilirubin": "serum bilirubin direct",
        "bilirubin indirect": "serum bilirubin indirect",
        "indirect bilirubin": "serum bilirubin indirect",
        # Liver - Enzymes
        "sgot": "aspartate aminotransferase",
        "sgot/ast": "aspartate aminotransferase",
        "ast": "aspartate aminotransferase",
        "sgpt": "alanine aminotransferase",
        "sgpt/alt": "alanine aminotransferase",
        "alt": "alanine aminotransferase",
        "alp": "alkaline phosphatase",
        "ggt": "gamma glutamyl transferase",
        # Liver - Proteins
        "total protein": "serum total protein",
        "albumin": "serum albumin",
        "globulin": "serum globulin calculated",
        "a/g ratio": "albumin globulin ratio",
        "albumin/globulin ratio": "albumin globulin ratio",
        "albumin :globulin ratio": "albumin globulin ratio",
        "a:g ratio": "albumin globulin ratio",
        # Lipids
        "total cholesterol": "total cholestrol",  # match registry typo
        "cholesterol total": "total cholestrol",
        "cholesterol": "total cholestrol",
        "triglycerides": "serum triglycerides",
        "hdl cholesterol": "serum hdl cholestrol",
        "hdl": "serum hdl cholestrol",
        "ldl cholesterol": "serum ldl cholestrol",
        "ldl": "serum ldl cholestrol",
        "vldl cholesterol": "serum vldl cholestrol",
        "vldl": "serum vldl cholestrol",
        "non hdl cholesterol": "non-hdl cholestrol",
        # Kidney
        "uric acid": "serum uric acid",
        "creatinine": "creatinine",
        "urea": "blood urea",
        "bun": "blood urea nitrogen",
        "calcium": "serum calcium",
        "phosphorus": "serum phosphorus",
        "sodium": "serum sodium",
        "potassium": "serum potassium",
        "chloride": "serum chloride",
        # Thyroid
        "tsh": "thyroid stimulating hormone",
        "t3": "free t3",
        "t4": "free t4",
        "free t3": "free t3",
        "free t4": "free t4",
        # Vitamins
        "vitamin d": "vitamin d 25-hydroxy",
        "25 hydroxy vitamin d": "vitamin d 25-hydroxy",
        "vitamin b12": "vitamin b12",
        # Iron
        "ferritin": "serum ferritin",
        "iron": "serum ferritin",
        # CBC - already have good aliases but add more
        "wbc count": "tlc",
        "total wbc count": "tlc",
        "white blood cell count": "tlc",
        "platelet count": "platelet count",
        "platelets": "platelet count",
        # More Lipid variations
        "vldl cholesterol": "serum vldl cholestrol",
        "vldl": "serum vldl cholestrol",
        "v l d l cholesterol": "serum vldl cholestrol",
        "chol/hdl ratio": "total cholestrol to hdl ratio",
        "total cholesterol/hdl ratio": "total cholestrol to hdl ratio",
        "ldl/hdl ratio": "ldl to hdl ratio",
        "hdl/ldl ratio": "ldl to hdl ratio",
        "hdl/ ldl ratio": "ldl to hdl ratio",
        # More Liver variations
        "bilirubin total": "serum bilirubin total",
        "bilirubin direct": "serum bilirubin direct", 
        "bilirubin indirect": "serum bilirubin indirect",
        "albumin/globulin ratio": "albumin/globulin ratio",
        "albumin:globulin ratio": "albumin/globulin ratio",
        "a/g ratio": "albumin/globulin ratio",
        "a:g ratio": "albumin/globulin ratio",
        "ag ratio": "albumin/globulin ratio",
        # Calcium variants
        "calcium serum": "serum calcium",
        "calcium": "serum calcium",
        # Vitamin variants  
        "vitamin - b12": "vitamin b12",
        "vitamin b-12": "vitamin b12",
        "cyanocobalamin": "vitamin b12",
        "vitamin d 25 hydroxy": "vitamin d 25-hydroxy",
        "vitamin d total 25 hydroxy": "vitamin d 25-hydroxy",
        "25 oh vitamin d": "vitamin d 25-hydroxy",
        "25 hydroxy vitamin d": "vitamin d 25-hydroxy",
        "folate": "folic acid",
        "folic acid": "folic acid",
        "folate folic acid": "folic acid",
        # Thyroid variants
        "thyroid stimulating hormone": "thyroid stimulating hormone tsh ultrasensitive",
        "thyroid stimulating hormone ultrasensitive": "thyroid stimulating hormone tsh ultrasensitive",
        "tsh ultrasensitive": "thyroid stimulating hormone tsh ultrasensitive",
        "tsh": "thyroid stimulating hormone tsh ultrasensitive",
        "triiodothyronine": "free t3",
        "triiodothyronine t3": "free t3",
        "t3": "free t3",
        "total thyroxine": "free t4",
        "total thyroxine t4": "free t4",
        "thyroxine": "free t4",
        "t4": "free t4",
        # Others
        "uric acid": "serum uric acid",
        "homocysteine": "homocysteine",
        "magnesium serum": "magnesium",
        "magnesium,serum": "magnesium",
        "insulin fasting": "insulin fasting",
        "fasting insulin": "insulin fasting",
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
        self._load_registry()

    def _load_registry(self) -> None:
        """Load biomarker registry and build alias lookup map."""
        stmt = select(BiomarkerRegistry)
        biomarkers = self.db.scalars(stmt).all()

        for biomarker in biomarkers:
            # Add canonical name
            normalized = self._normalize(biomarker.analyte_name)
            self._alias_map[normalized] = biomarker

            # Add aliases
            if biomarker.aliases:
                for alias in biomarker.aliases:
                    normalized_alias = self._normalize(alias)
                    if normalized_alias:
                        self._alias_map[normalized_alias] = biomarker

    # Parenthetical terms to preserve (important for disambiguation)
    PRESERVE_PARENS = {
        "total", "direct", "indirect", "fasting", "random", "ultrasensitive",
        "calculated", "serum", "plasma", "urine", "whole blood",
        "differential", "absolute", "cv", "sd",
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

    def _build_section_aware_labels(self, label: str, section: Optional[str]) -> list[tuple[str, float]]:
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
            results.extend([
                (f"{normalized} differential", 0.98),
                (f"{normalized} differential pct", 0.97),
                (f"{normalized} percent", 0.96),
                (f"differential {normalized}", 0.95),
                (f"{normalized} pct", 0.94),
            ])
        elif qualifier == "absolute":
            results.extend([
                (f"{normalized} absolute", 0.98),
                (f"{normalized} absolute count", 0.97),
                (f"absolute {normalized}", 0.96),
                (f"absolute {normalized} count", 0.95),
                (f"{normalized} count", 0.94),
            ])
        
        return results

    def canonicalize(self, raw_label: str, section: Optional[str] = None) -> CanonicalResult:
        """
        Attempt to match a raw label to the biomarker registry.
        
        Args:
            raw_label: The test name from the lab report
            section: Optional section context (e.g., "Differential Leucocyte Count")

        Returns:
            CanonicalResult with match info or unmatched status
        """
        if not raw_label or not raw_label.strip():
            return CanonicalResult(matched=False, match=None, raw_label=raw_label, section=section)

        # Try progressively more aggressive normalization
        attempts = []

        # 0. Section-aware labels first (highest priority for disambiguation)
        section_labels = self._build_section_aware_labels(raw_label, section)
        attempts.extend(section_labels)

        # 1. Basic normalization
        normalized = self._normalize(raw_label)
        attempts.append((normalized, 1.0))

        # 1.5. Check LABEL_SYNONYMS for common lab report variants
        if normalized in self.LABEL_SYNONYMS:
            synonym = self.LABEL_SYNONYMS[normalized]
            attempts.append((synonym, 0.98))
            attempts.append((self._normalize(synonym), 0.98))

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
        return CanonicalResult(matched=False, match=None, raw_label=raw_label, section=section)

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
        self._load_registry()
