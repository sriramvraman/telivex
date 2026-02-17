/**
 * Hook for document operations.
 */

import { useState, useCallback } from "react";
import { apiClient } from "../api/client";
import type { DocumentResponse, DocumentUploadResponse } from "../types";

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.listDocuments();
      setDocuments(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch documents");
    } finally {
      setLoading(false);
    }
  }, []);

  const uploadDocument = useCallback(
    async (
      file: { uri: string; name: string; type: string },
      collectedDate: string
    ): Promise<DocumentUploadResponse | null> => {
      setLoading(true);
      setError(null);
      try {
        const result = await apiClient.uploadDocument(file, collectedDate);
        // Refresh the document list after upload
        await fetchDocuments();
        return result;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to upload document");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [fetchDocuments]
  );

  return {
    documents,
    loading,
    error,
    fetchDocuments,
    uploadDocument,
  };
}
