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
    section: Optional[str] = None  # Parent section for context (e.g., "Differential Leucocyte Count")
    flag: Optional[str] = None  # Abnormal value indicator: 'L' for Low, 'H' for High


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
    
    # Flags indicating abnormal values (Low/High)
    ABNORMAL_FLAGS = re.compile(r"\s*[LH]\*?\s*$", re.IGNORECASE)
    
    UNIT_PATTERNS = [
        # Concentration units
        r"mg/dl", r"mg/dL",
        r"g/dl", r"g/dL", r"g/L",
        r"mmol/l", r"mmol/L",
        r"umol/l", r"umol/L", r"μmol/L",
        r"mEq/L", r"meq/l",
        r"ng/ml", r"ng/mL", r"ng/dL",
        r"pg/ml", r"pg/mL",
        r"ug/dL", r"µg/dL", r"mcg/dL",
        # Enzyme units
        r"IU/L", r"U/L", r"IU/mL", r"mIU/mL", r"mIU/L",
        # Cell counts - critical for CBC
        r"10\^3/µl", r"10\^3/uL", r"10\^3/µL",
        r"10\^6/µl", r"10\^6/uL", r"10\^6/µL",
        r"10\^9/L", r"x10\^9/L",
        r"10\^12/L", r"x10\^12/L",
        r"cells/uL", r"cells/µL", r"cells/μL",
        r"/µL", r"/uL", r"/µl",
        r"thou/µL", r"mill/µL",
        # RBC indices
        r"fl", r"fL",
        r"pg",
        r"%",
        # Time
        r"seconds", r"sec", r"mm/hr", r"mm/hour",
        # Ratios and others
        r"ratio", r"index",
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
                current_section: Optional[str] = None

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
                                "test description",
                                "parameter",
                                "analyte",
                                "value(s)",
                                "",
                            ):
                                continue

                            # Check if this is a section header (has label but no value)
                            if self._is_section_header(row):
                                current_section = str(row[0] or "").strip()
                                # Clean up section name (remove newlines, extra whitespace)
                                current_section = " ".join(current_section.split())
                                continue

                            extracted = self._parse_row(row, page_num, row_idx, current_section)
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

    def _is_section_header(self, row: list) -> bool:
        """
        Check if this row is a section header (has a label but no value/unit/range).
        
        Section headers like "Differential Leucocyte Count" or "RBC Parameters"
        provide context for the rows that follow.
        """
        if not row or not row[0]:
            return False
        
        first_cell = str(row[0] or "").strip()
        if not first_cell:
            return False
        
        # Check if remaining cells are empty or None
        other_cells = row[1:] if len(row) > 1 else []
        has_values = any(
            str(cell or "").strip() 
            for cell in other_cells 
            if cell is not None
        )
        
        # It's a section header if:
        # 1. First cell has text
        # 2. No values in other cells
        # 3. Doesn't look like a data row that failed to parse
        if not has_values:
            # Additional check: section headers typically don't contain numbers at the start
            if not re.match(r"^\d", first_cell):
                return True
        
        return False

    def _parse_row(
        self, row: list, page: int, row_index: int, section: Optional[str] = None
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
        flag: Optional[str] = None

        # Try to find value and unit in remaining cells
        for cell in non_empty[1:]:
            # Check if this cell contains a numeric value
            if value is None and self._looks_like_value(cell):
                # Extract any abnormal flag (L*/H*) from the value
                cell_clean, extracted_flag = self._extract_value_and_flag(cell)
                if extracted_flag:
                    flag = extracted_flag
                # Check if unit is attached to value
                value, extracted_unit = self._split_value_unit(cell_clean)
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

        # Clean up the label (remove method annotations like "colorimetric", "Calculated")
        label = self._clean_label(label)

        return ExtractedRow(
            label=label,
            value=value,
            unit=unit,
            reference_range=reference_range,
            page=page,
            row_index=row_index,
            section=section,
            flag=flag,
        )

    def _clean_label(self, label: str) -> str:
        """
        Clean up a label by removing method annotations and extra whitespace.
        
        Examples:
            "Hemoglobin\ncolorimetric" -> "Hemoglobin"
            "RBC Count\nElectrical impedance" -> "RBC Count"
            "PDW *\nCalculated" -> "PDW"
        """
        # Split on newline and take the first part (the actual test name)
        if "\n" in label:
            label = label.split("\n")[0]
        
        # Remove asterisks and clean up
        label = label.replace("*", "").strip()
        
        # Remove trailing periods (some labs use "Neutrophils." to distinguish)
        label = label.rstrip(".")
        
        return label

    # Words/phrases that indicate non-data rows (interpretation, comments, etc.)
    SKIP_LABELS = {
        # Headers
        "test", "test name", "parameter", "analyte", "result", "value",
        "unit", "units", "reference", "normal range", "specimen",
        # Interpretation/commentary
        "interpretation", "impression", "comment", "comments", "note", "notes",
        "remark", "remarks", "observation", "observations", "suggestion",
        "suggestions", "advice", "recommendation", "recommendations",
        "clinical correlation", "clinical significance", "please correlate",
        "clinically", "advised", "suggest", "indicates", "indicative",
        # Section markers
        "end of report", "report end", "verified by", "reported by",
        "authorized by", "checked by", "technician", "pathologist",
        "dr.", "doctor", "md", "mbbs",
    }
    
    # Patterns that indicate interpretation text (partial matches)
    SKIP_PATTERNS = [
        r"interpretation\s*:",
        r"impression\s*:",
        r"comment\s*:",
        r"note\s*:",
        r"^\s*-+\s*$",  # Just dashes
        r"^\s*\*+\s*$",  # Just asterisks
        r"please\s+(correlate|consult|see)",
        r"(within|outside)\s+normal\s+(limits|range)",
        r"values?\s+(are|is)\s+(normal|abnormal|high|low)",
        r"no\s+significant",
        r"(suggest|advised|recommend)",
        r"report\s+(verified|authorized|checked)",
        r"electronically\s+(signed|verified)",
    ]

    def _is_header_row(self, label: str) -> bool:
        """Check if this looks like a header or interpretation row to skip."""
        label_lower = label.lower().strip()
        
        # Exact match skip
        if label_lower in self.SKIP_LABELS:
            return True
        
        # Check for any skip label as a substring at the start
        for skip_word in self.SKIP_LABELS:
            if label_lower.startswith(skip_word):
                return True
        
        # Pattern-based skip
        for pattern in self.SKIP_PATTERNS:
            if re.search(pattern, label_lower):
                return True
        
        # Skip if label is too long (likely interpretation text)
        # Lab test names are typically < 50 chars
        if len(label) > 80:
            return True
        
        return False

    def _looks_like_value(self, cell: str) -> bool:
        """Check if cell looks like a numeric value."""
        # Remove common value indicators and abnormal flags
        cleaned = self.ABNORMAL_FLAGS.sub("", cell)
        cleaned = cleaned.replace(",", "").replace(" ", "")
        # Check for numeric pattern (possibly with unit attached)
        match = re.match(r"^[\d.]+", cleaned)
        return bool(match)
    
    def _extract_value_and_flag(self, cell: str) -> tuple[str, Optional[str]]:
        """
        Extract the numeric value and any abnormal flag (L*/H*).
        
        Returns:
            tuple of (clean_value, flag) where flag is 'L', 'H', or None
        """
        flag = None
        match = self.ABNORMAL_FLAGS.search(cell)
        if match:
            flag_text = match.group().strip().upper().replace("*", "")
            if flag_text in ("L", "H"):
                flag = flag_text
            cell = self.ABNORMAL_FLAGS.sub("", cell).strip()
        return cell, flag

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
