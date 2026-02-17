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


class Canonicalizer:
    """
    Matches raw extracted labels to the authoritative BiomarkerRegistry.

    Rules:
    - Matching is deterministic (no ML/probabilistic methods)
    - Exact alias match → confidence 1.0
    - Normalized match (case, whitespace) → confidence 0.95
    - No match → return unmatched, never guess
    """

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
        # Remove extra whitespace
        result = re.sub(r"\s+", " ", result)
        # Remove parenthetical content for matching (but not the whole thing)
        # e.g., "Hemoglobin (Hb)" → "hemoglobin"
        result_no_parens = re.sub(r"\s*\([^)]*\)\s*", " ", result).strip()
        if result_no_parens:
            result = result_no_parens
        return result

    def canonicalize(self, raw_label: str) -> CanonicalResult:
        """
        Attempt to match a raw label to the biomarker registry.

        Returns:
            CanonicalResult with match info or unmatched status
        """
        if not raw_label or not raw_label.strip():
            return CanonicalResult(matched=False, match=None, raw_label=raw_label)

        normalized = self._normalize(raw_label)

        # Try exact match on normalized form
        if normalized in self._alias_map:
            biomarker = self._alias_map[normalized]
            return CanonicalResult(
                matched=True,
                match=CanonicalMatch(
                    biomarker_id=biomarker.biomarker_id,
                    analyte_name=biomarker.analyte_name,
                    canonical_unit=biomarker.canonical_unit,
                    confidence=1.0,
                ),
                raw_label=raw_label,
            )

        # Try matching without common prefixes/suffixes
        variants = self._generate_variants(normalized)
        for variant in variants:
            if variant in self._alias_map:
                biomarker = self._alias_map[variant]
                return CanonicalResult(
                    matched=True,
                    match=CanonicalMatch(
                        biomarker_id=biomarker.biomarker_id,
                        analyte_name=biomarker.analyte_name,
                        canonical_unit=biomarker.canonical_unit,
                        confidence=0.95,
                    ),
                    raw_label=raw_label,
                )

        # No match found - do NOT guess
        return CanonicalResult(matched=False, match=None, raw_label=raw_label)

    def _generate_variants(self, normalized: str) -> list[str]:
        """Generate variants of the label to try matching."""
        variants = []

        # Remove common prefixes
        prefixes = ["serum ", "plasma ", "blood ", "urine ", "whole blood "]
        for prefix in prefixes:
            if normalized.startswith(prefix):
                variants.append(normalized[len(prefix) :])

        # Remove common suffixes
        suffixes = [" level", " levels", " count", " test", " assay"]
        for suffix in suffixes:
            if normalized.endswith(suffix):
                variants.append(normalized[: -len(suffix)])

        # Try without special characters
        no_special = re.sub(r"[^a-z0-9\s]", "", normalized)
        if no_special != normalized:
            variants.append(no_special)

        return variants

    def refresh(self) -> None:
        """Reload the registry (call after registry updates)."""
        self._alias_map.clear()
        self._load_registry()
