import { useCallback, useState } from "react";
import { uploadDocument } from "../api/client";
import type { UploadResponse } from "../types";

export function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [collectedDate, setCollectedDate] = useState(
    new Date().toISOString().split("T")[0],
  );
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) {
        if (selected.type !== "application/pdf") {
          setError("Only PDF files are supported");
          return;
        }
        setFile(selected);
        setError(null);
        setResult(null);
      }
    },
    [],
  );

  const handleUpload = useCallback(async () => {
    if (!file) return;

    setUploading(true);
    setError(null);
    setResult(null);

    try {
      const response = await uploadDocument(file, collectedDate);
      setResult(response);
      setFile(null);
      // Reset file input
      const fileInput = document.getElementById(
        "file-input",
      ) as HTMLInputElement;
      if (fileInput) fileInput.value = "";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }, [file, collectedDate]);

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        Upload Lab Report
      </h2>

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        {/* File Input */}
        <div>
          <label
            htmlFor="file-input"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            PDF File
          </label>
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
            <input
              id="file-input"
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              className="hidden"
            />
            <label htmlFor="file-input" className="cursor-pointer">
              {file ? (
                <div className="text-gray-900">
                  <p className="font-medium">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              ) : (
                <div className="text-gray-500">
                  <p className="text-4xl mb-2">📄</p>
                  <p className="font-medium">Click to select a PDF</p>
                  <p className="text-sm">or drag and drop</p>
                </div>
              )}
            </label>
          </div>
        </div>

        {/* Date Input */}
        <div>
          <label
            htmlFor="collected-date"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Collection Date
          </label>
          <input
            id="collected-date"
            type="date"
            value={collectedDate}
            onChange={(e) => setCollectedDate(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <p className="mt-1 text-sm text-gray-500">
            When were the samples collected?
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Success Display */}
        {result && (
          <div className="bg-green-50 border border-green-200 rounded-md p-4 space-y-2">
            <p className="text-green-700 font-medium">✓ Upload successful!</p>
            <ul className="text-sm text-green-600 space-y-1">
              <li>Document: {result.document.filename}</li>
              <li>Pages: {result.document.page_count}</li>
              <li>Events extracted: {result.events_created}</li>
              {result.unmapped_rows > 0 && (
                <li className="text-yellow-600">
                  ⚠ Unmapped rows: {result.unmapped_rows} (need review)
                </li>
              )}
            </ul>
          </div>
        )}

        {/* Upload Button */}
        <button
          type="button"
          onClick={handleUpload}
          disabled={!file || uploading}
          className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {uploading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin">⏳</span>
              Processing...
            </span>
          ) : (
            "Upload & Extract"
          )}
        </button>
      </div>

      {/* Instructions */}
      <div className="mt-8 bg-gray-100 rounded-lg p-6">
        <h3 className="font-medium text-gray-900 mb-2">
          How extraction works:
        </h3>
        <ol className="list-decimal list-inside text-sm text-gray-600 space-y-1">
          <li>Upload a PDF lab report</li>
          <li>Tables are detected and parsed automatically</li>
          <li>Biomarkers are matched against our registry</li>
          <li>Values are normalized to standard units</li>
          <li>Unrecognized items are flagged for review</li>
        </ol>
      </div>
    </div>
  );
}
