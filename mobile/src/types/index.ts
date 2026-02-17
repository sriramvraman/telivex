/**
 * TypeScript types mirroring backend Pydantic schemas.
 * Keep in sync with backend/app/schemas/
 */

// Document types
export interface DocumentResponse {
  document_id: string;
  filename: string;
  uploaded_at: string; // ISO datetime
  page_count: number | null;
  event_count: number;
  unmapped_count: number;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  page_count: number;
  events_created: number;
  unmapped_rows: number;
  message: string;
}

// Lab Event types
export interface LabEventResponse {
  event_id: string;
  biomarker_id: string;
  analyte_name: string;
  category: string | null;
  collected_at: string; // ISO datetime
  value_normalized: number;
  unit_canonical: string;
  value_original: number;
  unit_original: string;
  page: number | null;
  confidence: number;
  flag: "H" | "L" | null;  // H=High, L=Low, null=Normal
}

// Unmapped Row types
export interface UnmappedRowResponse {
  row_id: string;
  raw_label: string;
  raw_value: string | null;
  raw_unit: string | null;
  page: number | null;
  status: "pending" | "resolved" | "ignored";
  created_at: string; // ISO datetime
}

// Biomarker types
export interface BiomarkerResponse {
  biomarker_id: string;
  analyte_name: string;
  specimen: string;
  measurement_property: string | null;
  canonical_unit: string;
  category: string | null;
  panel_seed: string | null;
  is_derived: boolean;
  aliases: string[];
  default_reference_range_notes: string | null;
}

export interface BiomarkerListResponse {
  biomarkers: BiomarkerResponse[];
  total: number;
}

// Trend types (for chart visualization)
export interface TrendDataPoint {
  event_id: string;
  collected_at: string;
  value: number;
  unit: string;
}

export interface BiomarkerTrend {
  biomarker_id: string;
  analyte_name: string;
  unit: string;
  data_points: TrendDataPoint[];
}

// API Error type
export interface ApiError {
  detail: string;
  status_code?: number;
}

// Navigation param types
export type RootStackParamList = {
  DocumentList: undefined;
  Upload: undefined;
  DocumentDetail: { documentId: string };
  TrendViewer: { biomarkerId?: string };
};
