# Biomarker Registry Expansion Plan

## Goal
Expand from 76 biomarkers to ~200-300 commonly ordered tests in India, using LOINC + ABDM standards.

## Data Sources

### 1. LOINC (Primary backbone)
- **Source**: https://loinc.org/downloads/ (requires free registration)
- **Files needed**:
  - `LoincTable/Loinc.csv` - Main table with 100K+ codes
  - `AccessoryFiles/ComponentHierarchyBySystem/` - Organized by body system
- **Key fields**: LOINC_NUM, COMPONENT, PROPERTY, TIME_ASPCT, SYSTEM, SCALE_TYP
- **Filter for**: Laboratory class, common panels

### 2. ABDM (Indian context)
- **Source**: https://nrces.in/ndhm/fhir/r4/valueset-ndhm-lab-test-code.html
- **GitHub**: NHA ABDM publishes FHIR ValueSets
- **Contains**: LOINC codes with Indian lab name mappings

### 3. Indian Lab Catalogs (Aliases)
Scrape test names from:
- Redcliffe Labs (your current PDF source)
- Thyrocare
- SRL Diagnostics  
- Dr. Lal PathLabs
- Metropolis

## Schema Mapping

```
LOINC → Telivex Registry
─────────────────────────
LOINC_NUM        → biomarker_id (prefix: loinc:)
LONG_COMMON_NAME → analyte_name
SYSTEM           → specimen
PROPERTY         → measurement_property
EXAMPLE_UNITS    → canonical_unit
CLASSTYPE        → category (map: 1=Lab, 2=Clinical, etc.)
```

## Priority Panels (Phase 1)

| Panel | ~Tests | Priority |
|-------|--------|----------|
| Complete Blood Count (CBC) | 25 | ✅ Done |
| Liver Function (LFT) | 15 | ✅ Partial |
| Kidney Function (KFT/RFT) | 10 | ✅ Partial |
| Lipid Profile | 10 | ✅ Done |
| Thyroid Panel | 8 | ✅ Partial |
| Diabetes Panel (HbA1c, Glucose) | 5 | ✅ Done |
| Electrolytes | 6 | Needed |
| Iron Studies | 5 | Needed |
| Vitamin Panel | 8 | Partial |
| Urinalysis | 15 | Needed |
| Cardiac Markers | 8 | Needed |
| Inflammatory Markers | 5 | Needed |
| Hormones | 15 | Needed |
| Tumor Markers | 10 | Future |

## Missing from Current Registry (High Priority)

Based on your PDF analysis:
1. **P-LCR** - Platelet Large Cell Ratio
2. **P-LCC** - Platelet Large Cell Count
3. **eGFR** - Estimated Glomerular Filtration Rate
4. **Insulin (Fasting)**
5. **Magnesium**
6. **Folate/Folic Acid**
7. **Microalbumin**
8. **ATG** - Anti-Thyroglobulin Antibodies
9. **Homocysteine**
10. **Urinalysis components** (Volume, pH, Specific Gravity, etc.)

## Implementation Steps

### Step 1: Download LOINC (Manual)
1. Register at loinc.org
2. Download latest LOINC release
3. Extract relevant tables

### Step 2: Build LOINC-India Subset
```python
# Filter criteria:
# - CLASS = CHEM, HEM, SERO, UA (Chemistry, Hematology, Serology, Urinalysis)
# - CLASSTYPE = 1 (Laboratory)
# - Common panels only
```

### Step 3: Add Indian Aliases
```python
aliases = [
    # Common Indian lab naming patterns
    "S. Creatinine" → "Serum Creatinine"
    "SGPT" → "ALT"
    "SGOT" → "AST"
    "HbA1c" → "Glycated Hemoglobin"
    # Regional variations
    "Haemoglobin" / "Hemoglobin"
    # Abbreviations common in India
    "TLC" → "Total Leucocyte Count"
]
```

### Step 4: Validate with Sample PDFs
- Test against 5-10 real lab reports from different Indian labs
- Track match rate
- Add missing aliases iteratively

## Next Actions

1. [ ] User: Register at loinc.org and download LOINC database
2. [ ] Agent: Create script to parse LOINC and filter relevant tests
3. [ ] Agent: Build merged registry with LOINC codes + Indian aliases
4. [ ] User: Review and approve expanded registry
5. [ ] Agent: Create migration to update database

## Notes

- Keep existing 76 biomarkers as-is (they're working)
- Add new biomarkers incrementally
- Always use LOINC codes as biomarker_id for new entries
- Maintain backward compatibility with existing data
