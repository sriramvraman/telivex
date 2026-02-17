"""
Integration test: PDF extraction → canonicalization pipeline.
Tests with real lab report to verify section-aware matching.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from services.extractor import PDFExtractor


def test_extraction_with_sections():
    """Test that extraction preserves section context."""
    pdf_path = Path(__file__).parent.parent / "docs" / "sample_pdfs" / "155444719.pdf"
    
    if not pdf_path.exists():
        # Try alternate path
        pdf_path = Path(__file__).parent.parent.parent / "docs" / "sample_pdfs" / "155444719.pdf"
    
    if not pdf_path.exists():
        print(f"⚠️  Sample PDF not found at {pdf_path}")
        return
    
    extractor = PDFExtractor()
    result = extractor.extract(pdf_path)
    
    print(f"Extracted {len(result.rows)} rows from {result.page_count} pages")
    print(f"Errors: {result.errors}")
    print()
    
    # Find differential and absolute neutrophils
    diff_neutrophils = None
    abs_neutrophils = None
    
    for row in result.rows:
        if row.label.lower() == "neutrophils":
            if row.section and "differential" in row.section.lower():
                diff_neutrophils = row
            elif row.section and "absolute" in row.section.lower():
                abs_neutrophils = row
    
    print("=== Section Context Test ===")
    
    if diff_neutrophils:
        print(f"✅ Differential Neutrophils: {diff_neutrophils.value} {diff_neutrophils.unit} [section: {diff_neutrophils.section}]")
    else:
        print("❌ Differential Neutrophils NOT FOUND")
    
    if abs_neutrophils:
        print(f"✅ Absolute Neutrophils: {abs_neutrophils.value} {abs_neutrophils.unit} [section: {abs_neutrophils.section}]")
    else:
        print("❌ Absolute Neutrophils NOT FOUND")
    
    # Verify they're distinct
    if diff_neutrophils and abs_neutrophils:
        assert diff_neutrophils.value != abs_neutrophils.value, "Values should be different!"
        assert diff_neutrophils.unit != abs_neutrophils.unit, "Units should be different!"
        print("\n✅ PASS: Differential and Absolute counts are properly distinguished!")
    else:
        print("\n❌ FAIL: Could not find both counts")
    
    # Check units are captured
    print("\n=== Unit Capture Test ===")
    rows_with_units = [r for r in result.rows if r.unit]
    rows_without_units = [r for r in result.rows if not r.unit]
    
    print(f"Rows with units: {len(rows_with_units)}")
    print(f"Rows without units: {len(rows_without_units)}")
    
    # Show a few rows without units (these might be issues)
    if rows_without_units:
        print("\nRows missing units (potential issues):")
        for row in rows_without_units[:5]:
            print(f"  - {row.label}: {row.value} [section: {row.section}]")
    
    # Check flags
    print("\n=== Abnormal Flag Test ===")
    rows_with_flags = [r for r in result.rows if r.flag]
    print(f"Rows with abnormal flags: {len(rows_with_flags)}")
    for row in rows_with_flags[:10]:
        flag_emoji = "🔽" if row.flag == "L" else "🔼"
        print(f"  {flag_emoji} {row.label}: {row.value} {row.unit or ''} ({row.flag})")


if __name__ == "__main__":
    test_extraction_with_sections()
