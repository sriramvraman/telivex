"""PDF extraction service using pdfplumber."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pdfplumber


@dataclass
class ExtractedRow:
    """A single row extracted from a PDF table."""

    label: str
    value: Optional[str]
    unit: Optional[str]
    reference_range: Optional[str]
    page: int
    row_index: int


@dataclass
class ExtractionResult:
    """Result of PDF extraction."""

    rows: list[ExtractedRow]
    page_count: int
    lab_name: Optional[str]
    collected_date: Optional[str]
    errors: list[str]


class PDFExtractor:
    """
    Extracts structured data from lab report PDFs.

    Uses pdfplumber for table extraction. Does NOT perform canonicalization
    or unit normalization - that's handled by separate services.
    """

    # Common patterns for lab values
    VALUE_PATTERN = re.compile(r"^[\d.,]+$")
    UNIT_PATTERNS = [
        r"mg/dl",
        r"mg/dL",
        r"g/dl",
        r"g/dL",
        r"mmol/l",
        r"mmol/L",
        r"umol/l",
        r"μmol/L",
        r"mEq/L",
        r"meq/l",
        r"IU/L",
        r"U/L",
        r"%",
        r"cells/uL",
        r"cells/μL",
        r"x10\^9/L",
        r"x10\^12/L",
        r"fl",
        r"fL",
        r"pg",
        r"ng/ml",
        r"ng/mL",
        r"pg/ml",
        r"pg/mL",
        r"mIU/mL",
        r"seconds",
        r"sec",
    ]

    def __init__(self):
        self.unit_regex = re.compile(
            r"(" + "|".join(self.UNIT_PATTERNS) + r")", re.IGNORECASE
        )

    def extract(self, pdf_path: Path | str) -> ExtractionResult:
        """
        Extract lab data from a PDF file.

        Returns structured rows with raw labels, values, and units.
        Does not perform biomarker matching or unit conversion.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            return ExtractionResult(
                rows=[],
                page_count=0,
                lab_name=None,
                collected_date=None,
                errors=[f"File not found: {pdf_path}"],
            )

        rows: list[ExtractedRow] = []
        errors: list[str] = []
        lab_name: Optional[str] = None
        collected_date: Optional[str] = None

        try:
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract tables from this page
                    tables = page.extract_tables()

                    for table in tables:
                        if not table:
                            continue

                        for row_idx, row in enumerate(table):
                            if not row or not any(row):
                                continue

                            # Skip header rows (heuristic: contains common header words)
                            first_cell = str(row[0] or "").strip().lower()
                            if first_cell in (
                                "test",
                                "test name",
                                "parameter",
                                "analyte",
                                "",
                            ):
                                continue

                            extracted = self._parse_row(row, page_num, row_idx)
                            if extracted:
                                rows.append(extracted)

        except Exception as e:
            errors.append(f"PDF extraction error: {str(e)}")

        return ExtractionResult(
            rows=rows,
            page_count=page_count if "page_count" in dir() else 0,
            lab_name=lab_name,
            collected_date=collected_date,
            errors=errors,
        )

    def _parse_row(
        self, row: list, page: int, row_index: int
    ) -> Optional[ExtractedRow]:
        """
        Parse a table row into structured data.

        Handles various lab report formats with different column arrangements.
        """
        # Filter out None and empty cells
        cells = [str(c).strip() if c else "" for c in row]
        non_empty = [c for c in cells if c]

        if len(non_empty) < 2:
            return None

        # First non-empty cell is typically the label
        label = non_empty[0]

        # Skip rows that look like headers or metadata
        if self._is_header_row(label):
            return None

        value: Optional[str] = None
        unit: Optional[str] = None
        reference_range: Optional[str] = None

        # Try to find value and unit in remaining cells
        for cell in non_empty[1:]:
            # Check if this cell contains a numeric value
            if value is None and self._looks_like_value(cell):
                # Check if unit is attached to value
                value, extracted_unit = self._split_value_unit(cell)
                if extracted_unit and unit is None:
                    unit = extracted_unit
            # Check if this cell is a unit
            elif unit is None and self._looks_like_unit(cell):
                unit = cell
            # Check if this looks like a reference range
            elif reference_range is None and self._looks_like_range(cell):
                reference_range = cell

        # Must have at least a label and value
        if not label or not value:
            return None

        return ExtractedRow(
            label=label,
            value=value,
            unit=unit,
            reference_range=reference_range,
            page=page,
            row_index=row_index,
        )

    def _is_header_row(self, label: str) -> bool:
        """Check if this looks like a header row."""
        header_words = {
            "test",
            "test name",
            "parameter",
            "analyte",
            "result",
            "value",
            "unit",
            "units",
            "reference",
            "normal range",
            "specimen",
        }
        return label.lower() in header_words

    def _looks_like_value(self, cell: str) -> bool:
        """Check if cell looks like a numeric value."""
        # Remove common value indicators
        cleaned = cell.replace(",", "").replace(" ", "")
        # Check for numeric pattern (possibly with unit attached)
        match = re.match(r"^[\d.]+", cleaned)
        return bool(match)

    def _looks_like_unit(self, cell: str) -> bool:
        """Check if cell looks like a unit."""
        return bool(self.unit_regex.search(cell))

    def _looks_like_range(self, cell: str) -> bool:
        """Check if cell looks like a reference range."""
        # Common patterns: "10-20", "< 100", "> 50", "10 - 20 mg/dL"
        range_patterns = [
            r"\d+\s*-\s*\d+",  # 10-20 or 10 - 20
            r"[<>]\s*\d+",  # < 100 or > 50
            r"\d+\s*to\s*\d+",  # 10 to 20
        ]
        for pattern in range_patterns:
            if re.search(pattern, cell, re.IGNORECASE):
                return True
        return False

    def _split_value_unit(self, cell: str) -> tuple[str, Optional[str]]:
        """Split a cell into value and unit if unit is attached."""
        match = self.unit_regex.search(cell)
        if match:
            unit = match.group(1)
            value = cell[: match.start()].strip()
            return value, unit
        return cell, None
