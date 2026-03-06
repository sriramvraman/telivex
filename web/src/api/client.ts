/**
 * Telivex API Client
 * Handles all communication with the backend API.
 */

import type {
  AvailableTrend,
  Biomarker,
  Document,
  LabEvent,
  Trend,
  UnmappedRow,
  UploadResponse,
} from "../types";

const API_BASE = "/api/v1";
const TOKEN_KEY = "telivex_token";

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(
      errorBody.detail || `HTTP ${response.status}`,
      response.status,
    );
  }
  return response.json();
}

// ============ Document Endpoints ============

/** Upload a PDF document for extraction */
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  return handleResponse<UploadResponse>(response);
}

/** List all documents */
export async function listDocuments(): Promise<Document[]> {
  const response = await fetch(`${API_BASE}/documents`, {
    headers: authHeaders(),
  });
  return handleResponse<Document[]>(response);
}

/** Get a single document by ID */
export async function getDocument(documentId: string): Promise<Document> {
  const response = await fetch(`${API_BASE}/documents/${documentId}`);
  return handleResponse<Document>(response);
}

/** Get events extracted from a document */
export async function getDocumentEvents(
  documentId: string,
): Promise<LabEvent[]> {
  const response = await fetch(`${API_BASE}/documents/${documentId}/events`);
  return handleResponse<LabEvent[]>(response);
}

/** Get unmapped rows from a document */
export async function getDocumentUnmappedRows(
  documentId: string,
): Promise<UnmappedRow[]> {
  const response = await fetch(`${API_BASE}/documents/${documentId}/unmapped`);
  return handleResponse<UnmappedRow[]>(response);
}

/** Delete a document and all associated data */
export async function deleteDocument(documentId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/documents/${documentId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(
      errorBody.detail || `HTTP ${response.status}`,
      response.status,
    );
  }
}

// ============ Biomarker Endpoints ============

/** List all biomarkers in the registry */
export async function listBiomarkers(): Promise<Biomarker[]> {
  const response = await fetch(`${API_BASE}/biomarkers`);
  return handleResponse<Biomarker[]>(response);
}

/** Search biomarkers by name or alias */
export async function searchBiomarkers(query: string): Promise<Biomarker[]> {
  const response = await fetch(
    `${API_BASE}/biomarkers/search?q=${encodeURIComponent(query)}`,
  );
  return handleResponse<Biomarker[]>(response);
}

/** Get a single biomarker by ID */
export async function getBiomarker(biomarkerId: string): Promise<Biomarker> {
  const response = await fetch(`${API_BASE}/biomarkers/${biomarkerId}`);
  return handleResponse<Biomarker>(response);
}

// ============ Event Endpoints ============

/** List all events, optionally filtered by biomarker */
export async function listEvents(biomarkerId?: string): Promise<LabEvent[]> {
  const url = biomarkerId
    ? `${API_BASE}/events?biomarker_id=${biomarkerId}`
    : `${API_BASE}/events`;
  const response = await fetch(url);
  return handleResponse<LabEvent[]>(response);
}

/** Get a single event by ID */
export async function getEvent(eventId: string): Promise<LabEvent> {
  const response = await fetch(`${API_BASE}/events/${eventId}`);
  return handleResponse<LabEvent>(response);
}

// ============ Trend Endpoints ============

/** Get trend data for a biomarker */
export async function getTrend(biomarkerId: string): Promise<Trend> {
  const response = await fetch(`${API_BASE}/trends/${biomarkerId}`);
  return handleResponse<Trend>(response);
}

/** Get trends for multiple biomarkers */
export async function getTrends(biomarkerIds: string[]): Promise<Trend[]> {
  const params = biomarkerIds.map((id) => `ids=${id}`).join("&");
  const response = await fetch(`${API_BASE}/trends?${params}`);
  return handleResponse<Trend[]>(response);
}

/** List available trends (biomarkers with data) */
export async function listAvailableTrends(): Promise<AvailableTrend[]> {
  const response = await fetch(`${API_BASE}/trends`);
  return handleResponse<AvailableTrend[]>(response);
}

/** List categories with trend data */
export async function listTrendCategories(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/trends/categories/list`);
  return handleResponse<string[]>(response);
}

/** Get trend summary for a biomarker */
export async function getTrendSummary(biomarkerId: string): Promise<{
  biomarker_id: string;
  analyte_name: string;
  canonical_unit: string;
  category: string | null;
  reference_range: string | null;
  event_count: number;
  min_value: number | null;
  max_value: number | null;
  avg_value: number | null;
  first_date: string | null;
  last_date: string | null;
  latest_value: number | null;
}> {
  const response = await fetch(`${API_BASE}/trends/${biomarkerId}/summary`);
  return handleResponse(response);
}

export { ApiError };
