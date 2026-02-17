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
    CONVERSION_TABLE: dict[tuple[str, str], float] = {
        # Mass concentrations
        ("mg/dl", "mg/dl"): 1.0,
        ("mg/dl", "mg/dL"): 1.0,
        ("g/dl", "g/dL"): 1.0,
        ("g/dl", "mg/dl"): 1000.0,
        ("mg/l", "mg/dl"): 0.1,
        ("g/l", "g/dl"): 0.1,
        ("g/l", "mg/dl"): 100.0,
        # Molar concentrations
        ("mmol/l", "mmol/L"): 1.0,
        ("umol/l", "μmol/L"): 1.0,
        ("μmol/l", "μmol/L"): 1.0,
        ("nmol/l", "nmol/L"): 1.0,
        # Common biomarker-specific conversions
        # Glucose: mg/dL to mmol/L (factor: 0.0555)
        # Cholesterol: mg/dL to mmol/L (factor: 0.0259)
        # These should be applied per-biomarker, not globally
        # Enzyme units
        ("iu/l", "IU/L"): 1.0,
        ("u/l", "U/L"): 1.0,
        ("u/l", "IU/L"): 1.0,
        # Electrolytes
        ("meq/l", "mEq/L"): 1.0,
        ("mmol/l", "mEq/L"): 1.0,  # For monovalent ions
        # Cell counts
        ("cells/ul", "cells/μL"): 1.0,
        ("cells/μl", "cells/μL"): 1.0,
        ("/ul", "cells/μL"): 1.0,
        ("/μl", "cells/μL"): 1.0,
        ("x10^3/ul", "x10^9/L"): 1.0,
        ("x10^6/ul", "x10^12/L"): 1.0,
        ("10^3/ul", "x10^9/L"): 1.0,
        ("10^6/ul", "x10^12/L"): 1.0,
        # Percentages
        ("%", "%"): 1.0,
        ("percent", "%"): 1.0,
        # Volume units
        ("fl", "fL"): 1.0,
        # Mass units
        ("pg", "pg"): 1.0,
        ("ng/ml", "ng/mL"): 1.0,
        ("pg/ml", "pg/mL"): 1.0,
        ("ng/dl", "ng/dL"): 1.0,
        ("pg/dl", "pg/dL"): 1.0,
        ("ug/dl", "μg/dL"): 1.0,
        ("μg/dl", "μg/dL"): 1.0,
        # Hormones
        ("miu/ml", "mIU/mL"): 1.0,
        ("uiu/ml", "μIU/mL"): 1.0,
        # Time
        ("seconds", "seconds"): 1.0,
        ("sec", "seconds"): 1.0,
        ("s", "seconds"): 1.0,
        # Ratios (dimensionless)
        ("ratio", "ratio"): 1.0,
        ("", ""): 1.0,  # No unit
    }

    # Aliases for unit normalization
    UNIT_ALIASES: dict[str, str] = {
        "mg/dl": "mg/dl",
        "mg/dL": "mg/dl",
        "MG/DL": "mg/dl",
        "g/dl": "g/dl",
        "g/dL": "g/dl",
        "G/DL": "g/dl",
        "mmol/l": "mmol/l",
        "mmol/L": "mmol/l",
        "MMOL/L": "mmol/l",
        "umol/l": "umol/l",
        "μmol/l": "umol/l",
        "μmol/L": "umol/l",
        "iu/l": "iu/l",
        "IU/L": "iu/l",
        "u/l": "u/l",
        "U/L": "u/l",
        "meq/l": "meq/l",
        "mEq/L": "meq/l",
        "MEQ/L": "meq/l",
        "%": "%",
        "percent": "%",
        "fl": "fl",
        "fL": "fl",
        "FL": "fl",
        "pg": "pg",
        "PG": "pg",
        "ng/ml": "ng/ml",
        "ng/mL": "ng/ml",
        "NG/ML": "ng/ml",
        "pg/ml": "pg/ml",
        "pg/mL": "pg/ml",
        "cells/ul": "cells/ul",
        "cells/uL": "cells/ul",
        "cells/μL": "cells/ul",
        "/ul": "/ul",
        "/uL": "/ul",
        "/μL": "/ul",
        "x10^3/ul": "x10^3/ul",
        "x10^3/uL": "x10^3/ul",
        "10^3/ul": "10^3/ul",
        "10^3/uL": "10^3/ul",
        "x10^6/ul": "x10^6/ul",
        "x10^6/uL": "x10^6/ul",
        "10^6/ul": "10^6/ul",
        "10^6/uL": "10^6/ul",
        "seconds": "seconds",
        "sec": "sec",
        "secs": "sec",
        "s": "s",
        "miu/ml": "miu/ml",
        "mIU/mL": "miu/ml",
        "uiu/ml": "uiu/ml",
        "μIU/mL": "uiu/ml",
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
