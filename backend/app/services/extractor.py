"""PDF extraction service using pdfplumber."""

import re
from dataclasses import dataclass
from datetime import datetime
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
    section: Optional[str] = (
        None  # Parent section for context (e.g., "Differential Leucocyte Count")
    )
    flag: Optional[str] = None  # Abnormal value indicator: 'L' for Low, 'H' for High


@dataclass
class ExtractionResult:
    """Result of PDF extraction."""

    rows: list[ExtractedRow]
    page_count: int
    lab_name: Optional[str]
    collected_date: Optional[str]
    reported_date: Optional[str]
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
        r"mg/dl",
        r"mg/dL",
        r"g/dl",
        r"g/dL",
        r"g/L",
        r"mmol/l",
        r"mmol/L",
        r"umol/l",
        r"umol/L",
        r"μmol/L",
        r"mEq/L",
        r"meq/l",
        r"ng/ml",
        r"ng/mL",
        r"ng/dL",
        r"pg/ml",
        r"pg/mL",
        r"ug/dL",
        r"µg/dL",
        r"mcg/dL",
        # Enzyme units
        r"IU/L",
        r"U/L",
        r"IU/mL",
        r"mIU/mL",
        r"mIU/L",
        # Cell counts - critical for CBC
        r"10\^3/µl",
        r"10\^3/uL",
        r"10\^3/µL",
        r"10\^6/µl",
        r"10\^6/uL",
        r"10\^6/µL",
        r"10\^9/L",
        r"x10\^9/L",
        r"10\^12/L",
        r"x10\^12/L",
        r"cells/uL",
        r"cells/µL",
        r"cells/μL",
        r"/µL",
        r"/uL",
        r"/µl",
        r"thou/µL",
        r"mill/µL",
        # RBC indices
        r"fl",
        r"fL",
        r"pg",
        r"%",
        # Time
        r"seconds",
        r"sec",
        r"mm/hr",
        r"mm/hour",
        # Ratios and others
        r"ratio",
        r"index",
    ]

    # Date extraction patterns - labels that precede collection/report dates
    # Separated into collection-related and report-related for distinct extraction
    COLLECTED_DATE_LABELS = [
        r"collected?\s*(?:date|on)?",
        r"collection\s*date",
        r"sample\s*collected",
        r"specimen\s*collected",
        r"date\s*of\s*collection",
    ]

    REPORTED_DATE_LABELS = [
        r"report(?:ed)?\s*(?:date|on)?",
        r"date\s*of\s*report",
        r"report\s*generated",
    ]

    # Fallback labels (ambiguous - used only when specific labels not found)
    GENERIC_DATE_LABELS = [
        r"registered?\s*(?:date|on)?",
        r"received?\s*(?:date|on)?",
        r"date",
    ]

    # Combined for backward compat (used in fallback header scan)
    DATE_LABELS = (
        COLLECTED_DATE_LABELS + REPORTED_DATE_LABELS + GENERIC_DATE_LABELS
    )

    # Date format patterns (in order of preference)
    DATE_FORMATS = [
        # DD/MM/YYYY or DD-MM-YYYY (common in India)
        (r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", "%d/%m/%Y"),
        # DD-Mon-YYYY (e.g., 15-Jan-2024)
        (r"(\d{1,2})[/\-.\s]([A-Za-z]{3,9})[/\-.\s](\d{4})", "%d-%b-%Y"),
        # Mon DD, YYYY (e.g., Jan 15, 2024)
        (r"([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})", "%b %d %Y"),
        # YYYY-MM-DD (ISO format)
        (r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})", "%Y/%m/%d"),
        # DD Mon YYYY (e.g., 15 Jan 2024)
        (r"(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})", "%d %b %Y"),
    ]

    def __init__(self):
        self.unit_regex = re.compile(
            r"(" + "|".join(self.UNIT_PATTERNS) + r")", re.IGNORECASE
        )
        # Build separate date label patterns for collection vs report dates
        self.collected_date_regex = re.compile(
            r"(?:" + "|".join(self.COLLECTED_DATE_LABELS) + r")\s*:?\s*",
            re.IGNORECASE,
        )
        self.reported_date_regex = re.compile(
            r"(?:" + "|".join(self.REPORTED_DATE_LABELS) + r")\s*:?\s*",
            re.IGNORECASE,
        )
        # Combined pattern for fallback/generic matching
        self.date_label_regex = re.compile(
            r"(?:" + "|".join(self.DATE_LABELS) + r")\s*:?\s*", re.IGNORECASE
        )

    def _extract_dates(
        self, text: str
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Extract collection and report dates from PDF text.

        Looks for collection-related and report-related date labels separately.
        Returns (collected_date, reported_date) in YYYY-MM-DD format.
        Either or both may be None if not found.
        """
        if not text:
            return None, None

        collected_date: Optional[str] = None
        reported_date: Optional[str] = None

        lines = text.split("\n")
        for line in lines:
            # Try collection date labels
            if not collected_date:
                match = self.collected_date_regex.search(line)
                if match:
                    parsed = self._parse_date_string(line[match.end() :])
                    if parsed:
                        collected_date = parsed

            # Try report date labels
            if not reported_date:
                match = self.reported_date_regex.search(line)
                if match:
                    parsed = self._parse_date_string(line[match.end() :])
                    if parsed:
                        reported_date = parsed

            # Stop early if both found
            if collected_date and reported_date:
                break

        # Fallback: if neither found, try generic date labels
        if not collected_date and not reported_date:
            for line in lines:
                match = self.date_label_regex.search(line)
                if match:
                    parsed = self._parse_date_string(line[match.end() :])
                    if parsed:
                        # Assign to collected_date as the safer default
                        collected_date = parsed
                        break

        # Last resort: scan header for any date
        if not collected_date and not reported_date:
            header_text = "\n".join(lines[:20])
            for pattern, _ in self.DATE_FORMATS:
                match = re.search(pattern, header_text)
                if match:
                    parsed = self._parse_date_string(match.group(0))
                    if parsed:
                        collected_date = parsed
                        break

        return collected_date, reported_date

    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """
        Parse a date string and return YYYY-MM-DD format.

        Handles multiple date formats common in lab reports.
        """
        if not date_str:
            return None

        date_str = date_str.strip()

        # Try each format pattern
        for pattern, fmt in self.DATE_FORMATS:
            match = re.search(pattern, date_str)
            if match:
                try:
                    # Reconstruct the date string from the match
                    matched_str = match.group(0)

                    # Normalize separators for parsing
                    normalized = re.sub(r"[/\-.]", "/", matched_str)
                    normalized = re.sub(r"\s+", " ", normalized)
                    normalized = normalized.replace(",", "")

                    # Try to parse based on pattern type
                    if "Mon" in fmt or "b" in fmt.lower():
                        # Month name format - try multiple variations
                        for try_fmt in ["%d/%b/%Y", "%d %b %Y", "%b %d %Y", "%d-%b-%Y"]:
                            try:
                                parsed = datetime.strptime(normalized, try_fmt)
                                return parsed.strftime("%Y-%m-%d")
                            except ValueError:
                                continue
                    else:
                        # Numeric format
                        parts = re.split(r"[/\-.\s]+", normalized)
                        if len(parts) >= 3:
                            # Determine if it's DMY or YMD
                            if len(parts[0]) == 4:
                                # YYYY-MM-DD
                                year, month, day = (
                                    int(parts[0]),
                                    int(parts[1]),
                                    int(parts[2]),
                                )
                            else:
                                # DD-MM-YYYY (common in India)
                                day, month, year = (
                                    int(parts[0]),
                                    int(parts[1]),
                                    int(parts[2]),
                                )

                            # Validate
                            if (
                                1 <= month <= 12
                                and 1 <= day <= 31
                                and 1900 <= year <= 2100
                            ):
                                return f"{year:04d}-{month:02d}-{day:02d}"
                except (ValueError, IndexError):
                    continue

        return None

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
                reported_date=None,
                errors=[f"File not found: {pdf_path}"],
            )

        rows: list[ExtractedRow] = []
        errors: list[str] = []
        lab_name: Optional[str] = None
        collected_date: Optional[str] = None
        reported_date: Optional[str] = None

        try:
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
                current_section: Optional[str] = None

                # Try to extract dates from first page text
                if pdf.pages:
                    first_page_text = pdf.pages[0].extract_text() or ""
                    collected_date, reported_date = self._extract_dates(
                        first_page_text
                    )

                    # If either not found on first page, check second page
                    if (not collected_date or not reported_date) and len(
                        pdf.pages
                    ) > 1:
                        second_page_text = pdf.pages[1].extract_text() or ""
                        c2, r2 = self._extract_dates(second_page_text)
                        if not collected_date:
                            collected_date = c2
                        if not reported_date:
                            reported_date = r2

                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract tables from this page
                    tables = page.extract_tables()

                    if tables:
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

                                # Skip rows in interpretation sections
                                if current_section and self._is_interpretation_section(
                                    current_section
                                ):
                                    continue

                                extracted = self._parse_row(
                                    row, page_num, row_idx, current_section
                                )
                                if extracted:
                                    rows.append(extracted)
                    else:
                        # Fallback: extract from text when no tables found
                        text = page.extract_text() or ""
                        text_rows = self._extract_from_text(
                            text, page_num, current_section
                        )
                        for extracted in text_rows:
                            rows.append(extracted)
                        # Update current_section from text parsing
                        if text_rows:
                            last_section = text_rows[-1].section
                            if last_section:
                                current_section = last_section

        except Exception as e:
            errors.append(f"PDF extraction error: {str(e)}")

        return ExtractionResult(
            rows=rows,
            page_count=page_count if "page_count" in dir() else 0,
            lab_name=lab_name,
            collected_date=collected_date,
            reported_date=reported_date,
            errors=errors,
        )

    # Regex to match a lab data line: label, numeric value, optional unit, optional ref range
    # Examples:
    #   Glucose, Fasting 80 mg/dl 70- 100
    #   Hba1c (Glycosylated Hemoglobin) 5.70 % 4.2 - 5.7
    #   Serum Creatinine 0.73 mg/dl 0.7-1.3
    TEXT_DATA_LINE = re.compile(
        r"^(?P<label>.+?)\s+"  # Label (non-greedy, followed by whitespace)
        r"(?P<value>\d+[\d.,]*)"  # Numeric value
        r"(?:\s+(?P<unit>[^\d\s][^\s]*(?:/[^\s]+)?))?"  # Optional unit (starts with non-digit)
        r"(?:\s+(?P<ref>.*))?$"  # Optional reference range (rest of line)
    )

    # Lines to skip in text-based extraction
    TEXT_SKIP_PATTERNS = re.compile(
        r"^(?:"
        r"method\s*:|"  # Method lines
        r"patient\s*name|"  # Header lines
        r"age/gender|"
        r"order\s*id|"
        r"referred\s*by|"
        r"customer\s*since|"
        r"sample\s*(?:type|collected|received|temperature)|"
        r"report\s*(?:generated|status)|"
        r"department\s*of|"
        r"test\s*name\s+value|"  # Column headers
        r"page\s+\d+\s+of|"  # Page footers
        r"sin\s*no|"
        r"barcode|"
        r"\d+\s*/\s*\w+\s*/\s*\d+|"  # Date-only lines
        r"reference\s*:|"  # Reference lines in interpretation
        r"as\s+per\s+|"
        r"\*|"  # Lines starting with asterisk
        r"\d+\.\s+[A-Z]|"  # Numbered remarks (1. HbA1c is...)
        r"[a-z].*\.\s+[A-Z]"  # Sentences (prose text)
        r")",
        re.IGNORECASE,
    )

    # Labels from interpretation/reference sections that look like data but aren't
    TEXT_INTERP_LABELS = re.compile(
        r"(?:"
        r"at\s+risk|"
        r"diagnosing|"
        r"goals?\s+of|"
        r"therapeutic|"
        r"actions?\s+suggested|"
        r"age\s*>|"
        r"elevated|"
        r"borderline|"
        r"desirable|"
        r"optimal|"
        r"high\s*risk|"
        r"low\s*risk|"
        r"moderate\s*risk|"
        r"very\s+high|"
        r"near\s*/|"
        r"adults?\s+above|"
        r"goal\s+is|"
        r"non[\s-]diabetic|"
        r"insufficiency|"
        r"sufficiency|"
        r"vitamin\s*d\s*status|"
        r"first\s+trimester|"
        r"second\s+trimester|"
        r"third\s+trimester|"
        r"impaired\s+fasting|"
        r"diabetes\s*:|"
        r"normal\s*:|"
        r"pre[\s-]?diabetes|"
        r"^\d+[\d.]*\s*-\s*$|"  # Just "3.0 -" (partial range)
        r"^\d+[\d.]*\s*-\s*\d|"  # "3.0 - 6.0" (range line, no label)
        r"pus\s+cells|"  # Microscopy (non-quantitative)
        r"epithelial\s+cells|"  # Microscopy
        r"rbcs?\s+nil"  # Microscopy
        r")",
        re.IGNORECASE,
    )

    def _extract_from_text(
        self, text: str, page_num: int, current_section: Optional[str]
    ) -> list[ExtractedRow]:
        """
        Extract lab data from page text when no tables are found.

        Parses lines matching the pattern: <label> <value> <unit> <ref_range>
        """
        rows: list[ExtractedRow] = []
        in_interpretation = False

        for row_idx, line in enumerate(text.split("\n")):
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()

            # Skip known non-data lines
            if self.TEXT_SKIP_PATTERNS.match(line_lower):
                continue

            # Track interpretation sections
            if any(
                marker in line_lower
                for marker in (
                    "interpretation:",
                    "remarks",
                    "reference :",
                    "american diabetes",
                    "conditions that",
                    "a low level",
                    "ncep recommend",
                )
            ):
                in_interpretation = True
                continue

            # Skip lines in interpretation sections
            if in_interpretation:
                # Exit interpretation when we see a new test section header
                # (uppercase text without numbers, like "Kidney Function Test")
                if (
                    len(line) < 60
                    and not re.search(r"\d", line)
                    and line[0].isupper()
                    and not self._is_header_row(line)
                ):
                    current_section = line.strip()
                    in_interpretation = self._is_interpretation_section(current_section)
                    if not in_interpretation:
                        continue
                # Also exit if we see a clear data line with a known unit
                elif self.unit_regex.search(line) and self.TEXT_DATA_LINE.match(line):
                    in_interpretation = False
                else:
                    continue

            # Skip long lines (likely commentary/interpretation text)
            if len(line) > 120:
                continue

            # Try to match as a data line
            match = self.TEXT_DATA_LINE.match(line)
            if match:
                label = match.group("label").strip()
                value = match.group("value").strip()
                unit = match.group("unit")
                ref = match.group("ref")

                # Clean label
                label = self._clean_label(label)

                # Skip if label looks like a header or interpretation
                if self._is_header_row(label):
                    continue

                # Skip interpretation/reference labels
                if self.TEXT_INTERP_LABELS.search(label):
                    continue

                # Skip qualitative values like "Negative", "Normal", etc.
                if unit and unit.lower() in (
                    "negative",
                    "positive",
                    "normal",
                    "clear",
                    "yellow",
                    "pale",
                    "nil",
                    "absent",
                    "present",
                    "trace",
                    "hydroxy",
                ):
                    continue

                # Validate unit looks like a real unit
                if unit:
                    unit = unit.strip()
                    # Skip if "unit" is actually the start of ref range text
                    if unit.lower() in (
                        "desirable",
                        "optimal",
                        "borderline",
                        "high",
                        "low",
                        "near",
                        "ratio",
                        "years",
                    ):
                        if unit.lower() == "ratio":
                            ref = f"{unit} {ref}" if ref else unit
                            unit = None
                        else:
                            ref = f"{unit} {ref}" if ref else unit
                            unit = None

                # Skip entries with unit "mL" and label "Volume" (urine volume)
                if unit and unit.lower() == "ml":
                    continue

                # Skip entries without a recognized unit (likely noise)
                # Exception: ratios and some special tests
                if not unit and not any(
                    kw in label.lower()
                    for kw in ("ratio", "index", "gravity", "ph", "mentzer")
                ):
                    continue

                # Extract flag from value if present
                value_clean, flag = self._extract_value_and_flag(value)

                rows.append(
                    ExtractedRow(
                        label=label,
                        value=value_clean,
                        unit=unit,
                        reference_range=ref.strip() if ref else None,
                        page=page_num,
                        row_index=row_idx,
                        section=current_section,
                        flag=flag,
                    )
                )
            else:
                # Check if this is a section header
                if (
                    len(line) < 60
                    and not self._is_header_row(line)
                    and not any(c in line for c in ".;")
                    and not self.TEXT_INTERP_LABELS.search(line)
                ):
                    # Section headers: no digits, OR known patterns like "Test1 (KFT1)"
                    has_no_digits = not re.search(r"\d", line)
                    is_named_test = bool(
                        re.match(
                            r"^[A-Z][\w\s,()/-]+(?:Test|Profile|Panel|Count|Haemogram)",
                            line,
                        )
                    )
                    if has_no_digits or is_named_test:
                        current_section = line.strip()
                        in_interpretation = self._is_interpretation_section(
                            current_section
                        )

        return rows

    def _is_interpretation_section(self, section: str) -> bool:
        """Check if the current section is an interpretation/commentary section."""
        if not section:
            return False
        section_lower = section.lower()
        interpretation_markers = [
            "interpretation",
            "comment",
            "note:",
            "reference :",
            "remarks",
            "observation",
            "impression",
            "correlation",
            "criteria",
            "guidelines",
        ]
        return any(marker in section_lower for marker in interpretation_markers)

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
            str(cell or "").strip() for cell in other_cells if cell is not None
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
        # Interpretation/commentary
        "interpretation",
        "impression",
        "comment",
        "comments",
        "note",
        "notes",
        "remark",
        "remarks",
        "observation",
        "observations",
        "suggestion",
        "suggestions",
        "advice",
        "recommendation",
        "recommendations",
        "clinical correlation",
        "clinical significance",
        "please correlate",
        "clinically",
        "advised",
        "suggest",
        "indicates",
        "indicative",
        # Reference range labels (not actual tests)
        "normal",
        "optimal",
        "desirable",
        "borderline",
        "high",
        "low",
        "above optimal",
        "borderline high",
        "very high",
        "very low",
        "high risk",
        "very high risk",
        "low risk",
        "moderate risk",
        # Section markers
        "end of report",
        "report end",
        "verified by",
        "reported by",
        "authorized by",
        "checked by",
        "technician",
        "pathologist",
        "dr.",
        "doctor",
        "md",
        "mbbs",
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
