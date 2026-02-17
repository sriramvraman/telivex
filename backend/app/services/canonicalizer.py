"""
Canonicalization service - matches raw labels to biomarker registry.

Key principle: NEVER invent biomarker_ids. If no match found, surface as unmapped.
"""

import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BiomarkerRegistry


@dataclass
class CanonicalMatch:
    """Result of canonicalization attempt."""

    biomarker_id: str
    analyte_name: str
    canonical_unit: str
    confidence: float  # 1.0 = exact match, lower for fuzzy


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

    def _normalize(self, text: str) -> str:
        """Normalize text for matching: lowercase, strip whitespace, remove special chars."""
        if not text:
            return ""
        # Lowercase
        result = text.lower().strip()
        # Replace newlines with spaces
        result = result.replace("\n", " ").replace("\r", " ")
        # Remove extra whitespace
        result = re.sub(r"\s+", " ", result)
        # Remove parenthetical content for matching
        result_no_parens = re.sub(r"\s*\([^)]*\)\s*", " ", result).strip()
        if result_no_parens:
            result = result_no_parens
        # Remove trailing asterisks and flags
        result = re.sub(r"\s*\*+\s*$", "", result)
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
                return CanonicalResult(
                    matched=True,
                    match=CanonicalMatch(
                        biomarker_id=biomarker.biomarker_id,
                        analyte_name=biomarker.analyte_name,
                        canonical_unit=biomarker.canonical_unit,
                        confidence=confidence,
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
