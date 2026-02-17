/**
 * API client for Telivex backend.
 * Base URL configured for local development.
 */

import type {
  DocumentResponse,
  DocumentUploadResponse,
  LabEventResponse,
  UnmappedRowResponse,
  BiomarkerListResponse,
  BiomarkerTrend,
  ApiError,
} from "../types";

// Use localhost for iOS simulator, 10.0.2.2 for Android emulator
// In production, this would be the deployed API URL
const API_BASE_URL = __DEV__
  ? "http://192.168.1.2:8001/api/v1"
  : "https://api.telivex.health/api/v1";

class TelivexApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        Accept: "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
        status_code: response.status,
      }));
      throw new Error(error.detail || "API request failed");
    }

    return response.json();
  }

  // Document endpoints
  async listDocuments(): Promise<DocumentResponse[]> {
    return this.request<DocumentResponse[]>("/documents/");
  }

  async getDocument(documentId: string): Promise<DocumentResponse> {
    return this.request<DocumentResponse>(`/documents/${documentId}`);
  }

  async uploadDocument(
    file: { uri: string; name: string; type: string },
    collectedDate: string
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();

    // React Native file format for FormData
    formData.append("file", {
      uri: file.uri,
      name: file.name,
      type: file.type,
    } as any);

    return this.request<DocumentUploadResponse>(
      `/documents/upload?collected_date=${encodeURIComponent(collectedDate)}`,
      {
        method: "POST",
        body: formData,
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
  }

  async getDocumentEvents(documentId: string): Promise<LabEventResponse[]> {
    return this.request<LabEventResponse[]>(`/documents/${documentId}/events`);
  }

  async getUnmappedRows(documentId: string): Promise<UnmappedRowResponse[]> {
    return this.request<UnmappedRowResponse[]>(
      `/documents/${documentId}/unmapped`
    );
  }

  // Biomarker endpoints
  async listBiomarkers(
    category?: string,
    search?: string
  ): Promise<BiomarkerListResponse> {
    const params = new URLSearchParams();
    if (category) params.append("category", category);
    if (search) params.append("search", search);

    const queryString = params.toString();
    const endpoint = `/biomarkers/${queryString ? `?${queryString}` : ""}`;

    return this.request<BiomarkerListResponse>(endpoint);
  }

  // Trend endpoints (to be implemented on backend)
  async getBiomarkerTrend(biomarkerId: string): Promise<BiomarkerTrend> {
    return this.request<BiomarkerTrend>(`/trends/${biomarkerId}`);
  }

  async getAllTrends(): Promise<BiomarkerTrend[]> {
    return this.request<BiomarkerTrend[]>("/trends/");
  }

  // Lab Event endpoints
  async listEvents(
    biomarkerId?: string,
    fromDate?: string,
    toDate?: string
  ): Promise<LabEventResponse[]> {
    const params = new URLSearchParams();
    if (biomarkerId) params.append("biomarker_id", biomarkerId);
    if (fromDate) params.append("from_date", fromDate);
    if (toDate) params.append("to_date", toDate);

    const queryString = params.toString();
    const endpoint = `/events/${queryString ? `?${queryString}` : ""}`;

    return this.request<LabEventResponse[]>(endpoint);
  }
}

// Export singleton instance
export const apiClient = new TelivexApiClient();

// Also export class for testing with different base URL
export { TelivexApiClient };
