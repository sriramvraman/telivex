import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { uploadDocument } from "../api/client";
import type { UploadResponse } from "../types";

export function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
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
      const response = await uploadDocument(file);
      setResult(response);
      setFile(null);
      const fileInput = document.getElementById(
        "file-input",
      ) as HTMLInputElement;
      if (fileInput) fileInput.value = "";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }, [file]);

  return (
    <div className="max-w-xl mx-auto">
      <h2 className="text-xl font-semibold text-slate-900 mb-6">
        Upload Lab Report
      </h2>

      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-5">
        {/* File Input */}
        <div>
          <label
            htmlFor="file-input"
            className="block text-sm font-medium text-slate-700 mb-1.5"
          >
            PDF File
          </label>
          <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center hover:border-brand-400 transition-colors cursor-pointer">
            <input
              id="file-input"
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              className="hidden"
            />
            <label htmlFor="file-input" className="cursor-pointer">
              {file ? (
                <div>
                  <p className="font-medium text-slate-900">{file.name}</p>
                  <p className="text-sm text-slate-400 mt-0.5">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              ) : (
                <div className="text-slate-400">
                  <svg
                    className="w-8 h-8 mx-auto mb-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    role="img"
                    aria-label="Upload"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                  <p className="text-sm font-medium">Click to select a PDF</p>
                  <p className="text-xs mt-0.5">
                    Dates will be extracted automatically from the report
                  </p>
                </div>
              )}
            </label>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Success */}
        {result && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 space-y-2">
            <p className="text-sm font-medium text-emerald-700">
              Upload successful
            </p>
            <p className="text-sm text-emerald-600">{result.message}</p>
            <Link
              to={`/documents/${result.document_id}`}
              className="inline-block text-sm font-medium text-brand-600 hover:text-brand-700 mt-1"
            >
              View document details &rarr;
            </Link>
          </div>
        )}

        {/* Upload */}
        <button
          type="button"
          onClick={handleUpload}
          disabled={!file || uploading}
          className="w-full py-2.5 px-4 bg-brand-600 text-white font-medium rounded-lg hover:bg-brand-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed transition-colors"
        >
          {uploading ? "Processing..." : "Upload & Extract"}
        </button>
      </div>
    </div>
  );
}
