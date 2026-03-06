import { useState } from "react";
import { Link } from "react-router-dom";
import { deleteDocument, listDocuments } from "../api/client";
import { useApi } from "../hooks/useApi";
import type { Document } from "../types";

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function DocumentsPage() {
  const { data: documents, loading, error, refetch } = useApi(listDocuments);
  const [deleting, setDeleting] = useState<string | null>(null);

  async function handleDelete(doc: Document) {
    if (
      !window.confirm(
        `Delete "${doc.filename}"? This removes all extracted data.`,
      )
    )
      return;
    setDeleting(doc.document_id);
    try {
      await deleteDocument(doc.document_id);
      refetch();
    } catch {
      // refetch to show current state
      refetch();
    } finally {
      setDeleting(null);
    }
  }

  if (loading) {
    return (
      <div className="text-center py-16 text-slate-400">
        Loading documents...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <p className="text-red-600 mb-4">{error}</p>
        <button
          type="button"
          onClick={refetch}
          className="text-brand-600 hover:underline text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Documents</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {documents?.length ?? 0} lab reports uploaded
          </p>
        </div>
        <Link
          to="/"
          className="px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 transition-colors"
        >
          Upload New
        </Link>
      </div>

      {documents && documents.length > 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/50">
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Filename
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Collected
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Reported
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Uploaded
                </th>
                <th className="text-center px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Events
                </th>
                <th className="text-center px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Unmapped
                </th>
                <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {documents.map((doc: Document) => (
                <tr
                  key={doc.document_id}
                  className="hover:bg-brand-50/30 transition-colors group"
                >
                  <td className="px-5 py-3.5">
                    <Link
                      to={`/documents/${doc.document_id}`}
                      className="font-medium text-slate-900 group-hover:text-brand-700 transition-colors"
                    >
                      {doc.filename}
                    </Link>
                  </td>
                  <td className="px-5 py-3.5 text-sm text-slate-500">
                    {doc.collected_at ? (
                      formatDate(doc.collected_at)
                    ) : (
                      <span className="text-slate-300">&mdash;</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-sm text-slate-500">
                    {doc.reported_at ? (
                      formatDate(doc.reported_at)
                    ) : (
                      <span className="text-slate-300">&mdash;</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-sm text-slate-500">
                    {formatDate(doc.uploaded_at)}
                  </td>
                  <td className="px-5 py-3.5 text-center">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-brand-50 text-brand-700">
                      {doc.event_count}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-center">
                    {doc.unmapped_count > 0 ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700">
                        {doc.unmapped_count}
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400">0</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-center">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        handleDelete(doc);
                      }}
                      disabled={deleting === doc.document_id}
                      className="text-slate-300 hover:text-red-500 transition-colors disabled:opacity-50"
                      title="Delete document"
                    >
                      {deleting === doc.document_id ? (
                        <svg
                          className="w-4 h-4 animate-spin"
                          fill="none"
                          viewBox="0 0 24 24"
                          role="img"
                          aria-label="Deleting"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          />
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                          />
                        </svg>
                      ) : (
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                          role="img"
                          aria-label="Delete"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={1.5}
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      )}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 p-16 text-center">
          <div className="w-12 h-12 bg-slate-100 rounded-xl flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-6 h-6 text-slate-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              role="img"
              aria-label="No documents"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <p className="text-slate-500 mb-3">No documents uploaded yet</p>
          <Link
            to="/"
            className="text-brand-600 hover:text-brand-700 text-sm font-medium"
          >
            Upload your first lab report
          </Link>
        </div>
      )}
    </div>
  );
}
