// API Types for Telivex Health Platform

/** Document metadata returned from the API */
export interface Document {
  id: string;
  filename: string;
  uploaded_at: string;
  page_count: number;
  file_hash: string;
  storage_path: string;
}

/** Biomarker from the registry */
export interface Biomarker {
  biomarker_id: string;
  analyte_name: string;
  specimen: string;
  measurement_property: string;
  canonical_unit: string;
  category: string;
  aliases: string[];
  is_derived: boolean;
}

/** Lab event with provenance */
export interface LabEvent {
  event_id: string;
  biomarker_id: string;
  analyte_name: string;
  category: string | null;
  document_id: string;
  collected_at: string;
  value_original: number;
  unit_original: string;
  value_normalized: number | null;
  unit_canonical: string | null;
  panel_name: string | null;
  lab_name: string | null;
  page: number;
  confidence: number;
  source_type: "pdf" | "manual" | "import";
  created_at: string;
}

/** Unmapped row from extraction */
export interface UnmappedRow {
  row_id: string;
  document_id: string;
  raw_label: string;
  raw_value: string;
  raw_unit: string | null;
  page: number;
  status: "pending" | "resolved" | "ignored";
  resolved_biomarker_id: string | null;
}

/** Trend point for time-series display */
export interface TrendPoint {
  event_id: string;
  collected_at: string;
  value: number;
  unit: string;
  document_id: string;
  page: number;
}

/** Trend response for a biomarker */
export interface Trend {
  biomarker_id: string;
  biomarker_name: string;
  canonical_unit: string;
  points: TrendPoint[];
}

/** Upload response from document upload */
export interface UploadResponse {
  document: Document;
  events_created: number;
  unmapped_rows: number;
}

/** API error response */
export interface ApiError {
  detail: string;
}
