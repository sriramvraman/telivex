"""
Unit normalization service - converts values to canonical units.

Key principle: All conversions are DETERMINISTIC using lookup tables.
No probabilistic inference. Unknown conversions are flagged, not guessed.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class NormalizationResult:
    """Result of unit normalization."""

    success: bool
    value_normalized: float
    unit_canonical: str
    value_original: float
    unit_original: str
    error: Optional[str] = None


class UnitNormalizer:
    """
    Converts lab values to canonical units.

    All conversions use deterministic lookup tables.
    If a conversion is not in the table, it fails explicitly.
    """

    # Unit normalization lookup table
    # Format: (from_unit_normalized, to_unit) -> conversion_factor
    # value_canonical = value_original * factor
    #
    # Design: preserve original values, convert to LOINC canonical units.
    # Indian labs report in local conventions; we normalize to comparable units.
    CONVERSION_TABLE: dict[tuple[str, str], float] = {
        # === Identity conversions (same unit, different notation) ===
        ("mg/dl", "mg/dL"): 1.0,
        ("g/dl", "g/dL"): 1.0,
        ("%", "%"): 1.0,
        ("fl", "fL"): 1.0,
        ("pg", "pg"): 1.0,
        ("ng/ml", "ng/mL"): 1.0,
        ("pg/ml", "pg/mL"): 1.0,
        ("ng/dl", "ng/dL"): 1.0,
        ("ug/dl", "µg/dL"): 1.0,
        ("µg/dl", "µg/dL"): 1.0,
        ("u/l", "U/L"): 1.0,
        ("iu/l", "U/L"): 1.0,
        ("mm/hr", "mm/hr"): 1.0,
        ("mmol/l", "mmol/L"): 1.0,
        ("umol/l", "µmol/L"): 1.0,
        ("µmol/l", "µmol/L"): 1.0,
        ("meq/l", "mmol/L"): 1.0,  # For monovalent ions (Na, K, Cl)
        ("miu/l", "mIU/L"): 1.0,
        ("uiu/ml", "µIU/mL"): 1.0,
        ("uiu/ml", "mIU/L"): 1.0,  # µIU/mL = mIU/L
        ("seconds", "seconds"): 1.0,
        ("sec", "seconds"): 1.0,
        ("ratio", "ratio"): 1.0,
        ("", ""): 1.0,
        ("", "ratio"): 1.0,
        # === Cell count conversions ===
        # 10^3/µL = 10*9/L (same value, different notation)
        ("10^3/µl", "10*9/L"): 1.0,
        ("10^3/ul", "10*9/L"): 1.0,
        ("x10^3/ul", "10*9/L"): 1.0,
        ("10^9/l", "10*9/L"): 1.0,
        # 10^6/µL = 10*12/L (same value, different notation)
        ("10^6/µl", "10*12/L"): 1.0,
        ("10^6/ul", "10*12/L"): 1.0,
        ("x10^6/ul", "10*12/L"): 1.0,
        ("10^12/l", "10*12/L"): 1.0,
        # === Missing unit passthrough for absolute counts ===
        # When lab omits unit but value is in 10^3/µL (absolute WBC counts)
        ("", "10*9/L"): 1.0,
        # === Mass concentration conversions ===
        ("g/dl", "mg/dL"): 1000.0,
        ("mg/l", "mg/dL"): 0.1,
        ("g/l", "g/dL"): 0.1,
        ("g/l", "mg/dL"): 100.0,
        # === Thyroid ===
        ("miu/l", "µIU/mL"): 1.0,  # TSH: mIU/L = µIU/mL
        ("ng/dl", "pg/mL"): 10.0,  # T3: ng/dL → pg/mL
        ("µg/dl", "ng/dL"): 1000.0,  # T4: µg/dL to ng/dL
        # === Iron ===
        ("µg/dl", "ng/mL"): 10.0,  # 1 µg/dL = 10 ng/mL
        # === Electrolytes ===
        # mmol/L to mg/dL conversions (magnesium, calcium, phosphorus)
        ("mmol/l", "mg/dL"): 1.0,  # Will be overridden per-biomarker when needed
        # === Albumin: handle missing unit ===
        ("", "g/dL"): 1.0,
        # === Percentage to ratio ===
        ("%", "ratio"): 0.01,
    }

    # Aliases for unit normalization: map all variants to a canonical lowercase form
    UNIT_ALIASES: dict[str, str] = {
        # Mass concentration
        "mg/dl": "mg/dl",
        "mg/dL": "mg/dl",
        "MG/DL": "mg/dl",
        "g/dl": "g/dl",
        "g/dL": "g/dl",
        "G/DL": "g/dl",
        "gm%": "g/dl",
        "gm/dl": "g/dl",
        "mg/l": "mg/l",
        "mg/L": "mg/l",
        "g/l": "g/l",
        "g/L": "g/l",
        # Molar concentration
        "mmol/l": "mmol/l",
        "mmol/L": "mmol/l",
        "MMOL/L": "mmol/l",
        "umol/l": "µmol/l",
        "µmol/l": "µmol/l",
        "μmol/l": "µmol/l",
        "µmol/L": "µmol/l",
        "μmol/L": "µmol/l",
        # Enzyme units
        "u/l": "u/l",
        "U/L": "u/l",
        "iu/l": "u/l",
        "IU/L": "u/l",  # IU/L = U/L for enzymes
        # Electrolytes
        "meq/l": "meq/l",
        "mEq/L": "meq/l",
        "MEQ/L": "meq/l",
        # Percentages
        "%": "%",
        "percent": "%",
        # Volume/mass units
        "fl": "fl",
        "fL": "fl",
        "FL": "fl",
        "pg": "pg",
        "PG": "pg",
        # Concentration units
        "ng/ml": "ng/ml",
        "ng/mL": "ng/ml",
        "ng/Ml": "ng/ml",
        "pg/ml": "pg/ml",
        "pg/mL": "pg/ml",
        "ng/dl": "ng/dl",
        "ng/dL": "ng/dl",
        "ug/dl": "µg/dl",
        "µg/dL": "µg/dl",
        "μg/dL": "µg/dl",
        # Cell counts
        "10^3/µl": "10^3/µl",
        "10^3/μl": "10^3/µl",
        "10^3/μL": "10^3/µl",
        "10^3/ul": "10^3/µl",
        "10^3/uL": "10^3/µl",
        "x10^3/ul": "10^3/µl",
        "x10^3/uL": "10^3/µl",
        "10^6/µl": "10^6/µl",
        "10^6/μl": "10^6/µl",
        "10^6/ul": "10^6/µl",
        "10^6/uL": "10^6/µl",
        "x10^6/ul": "10^6/µl",
        "x10^6/uL": "10^6/µl",
        "10*9/L": "10^3/µl",  # LOINC notation → lab notation (same value)
        "10*12/L": "10^6/µl",  # LOINC notation → lab notation (same value)
        "10^9/l": "10^3/µl",
        "10^9/L": "10^3/µl",
        "10^12/l": "10^6/µl",
        "10^12/L": "10^6/µl",
        # Indian lab cell count notations
        "millions/cumm": "10^6/µl",
        "mill/cumm": "10^6/µl",
        "thou/cumm": "10^3/µl",
        "thousands/cumm": "10^3/µl",
        # ESR
        "mm/hr": "mm/hr",
        "mm/h": "mm/hr",
        "mm/1st": "mm/hr",
        "mm/1sthr": "mm/hr",
        # Time
        "seconds": "seconds",
        "sec": "sec",
        "secs": "sec",
        "s": "sec",
        # Hormones
        "miu/l": "miu/l",
        "mIU/L": "miu/l",
        "miu/ml": "miu/l",
        "mIU/mL": "miu/l",  # mIU/mL = mIU/L for practical purposes
        "uiu/ml": "uiu/ml",
        "µIU/mL": "uiu/ml",
        "µIU/ml": "uiu/ml",
        "μIU/mL": "uiu/ml",
        "μIU/ml": "uiu/ml",
        # Ratios
        "ratio": "ratio",
        "Ratio": "ratio",
    }

    def normalize(
        self, value: str | float, unit: Optional[str], canonical_unit: str
    ) -> NormalizationResult:
        """
        Normalize a value to its canonical unit.

        Args:
            value: The original value (as string or float)
            unit: The original unit (may be None)
            canonical_unit: The target canonical unit from the registry

        Returns:
            NormalizationResult with normalized value or error
        """
        # Parse value
        try:
            if isinstance(value, str):
                # Remove commas and whitespace
                cleaned = value.replace(",", "").strip()
                value_float = float(cleaned)
            else:
                value_float = float(value)
        except (ValueError, TypeError):
            return NormalizationResult(
                success=False,
                value_normalized=0.0,
                unit_canonical=canonical_unit,
                value_original=0.0,
                unit_original=unit or "",
                error=f"Cannot parse value: {value}",
            )

        # Handle missing unit
        unit_original = unit or ""
        if not unit_original:
            # If no unit provided and canonical unit is also empty, it's likely a ratio
            if not canonical_unit or canonical_unit in ("ratio", "%", ""):
                return NormalizationResult(
                    success=True,
                    value_normalized=value_float,
                    unit_canonical=canonical_unit or "",
                    value_original=value_float,
                    unit_original="",
                )

        # Normalize the unit string
        unit_normalized = self.UNIT_ALIASES.get(
            unit_original, unit_original.lower().strip()
        )
        canonical_normalized = self.UNIT_ALIASES.get(
            canonical_unit, canonical_unit.lower().strip()
        )

        # Check if units are already the same
        if unit_normalized == canonical_normalized:
            return NormalizationResult(
                success=True,
                value_normalized=value_float,
                unit_canonical=canonical_unit,
                value_original=value_float,
                unit_original=unit_original,
            )

        # Look up conversion factor
        conversion_key = (unit_normalized, canonical_unit)
        if conversion_key in self.CONVERSION_TABLE:
            factor = self.CONVERSION_TABLE[conversion_key]
            return NormalizationResult(
                success=True,
                value_normalized=value_float * factor,
                unit_canonical=canonical_unit,
                value_original=value_float,
                unit_original=unit_original,
            )

        # Try reverse lookup with canonical_normalized
        conversion_key_alt = (unit_normalized, canonical_normalized)
        if conversion_key_alt in self.CONVERSION_TABLE:
            factor = self.CONVERSION_TABLE[conversion_key_alt]
            return NormalizationResult(
                success=True,
                value_normalized=value_float * factor,
                unit_canonical=canonical_unit,
                value_original=value_float,
                unit_original=unit_original,
            )

        # No conversion found - fail explicitly
        return NormalizationResult(
            success=False,
            value_normalized=value_float,  # Return original value
            unit_canonical=canonical_unit,
            value_original=value_float,
            unit_original=unit_original,
            error=f"No conversion from '{unit_original}' to '{canonical_unit}'",
        )
