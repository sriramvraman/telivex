import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  deleteDocument,
  getDocumentEvents,
  getDocumentUnmappedRows,
  listDocuments,
} from "../api/client";
import { useApi } from "../hooks/useApi";
import type { Document, LabEvent, UnmappedRow } from "../types";

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Group events by category */
function groupEventsByCategory(
  events: LabEvent[],
): Map<string, LabEvent[]> {
  const groups = new Map<string, LabEvent[]>();
  for (const event of events) {
    const category = event.category || "Uncategorized";
    if (!groups.has(category)) {
      groups.set(category, []);
    }
    groups.get(category)!.push(event);
  }
  return groups;
}

/** Collapsible panel component */
function CollapsiblePanel({
  title,
  count,
  children,
  defaultOpen = false,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border rounded-lg overflow-hidden mb-3">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between transition-colors"
      >
        <span className="font-medium text-gray-900">{title}</span>
        <span className="flex items-center gap-2">
          <span className="text-sm text-gray-500 bg-gray-200 px-2 py-0.5 rounded">
            {count}
          </span>
          <span
            className={`transform transition-transform ${isOpen ? "rotate-180" : ""}`}
          >
            ▼
          </span>
        </span>
      </button>
      {isOpen && <div className="p-2 bg-white">{children}</div>}
    </div>
  );
}

interface DocumentDetailProps {
  document: Document;
  onClose: () => void;
  onDelete: () => void;
}

function DocumentDetail({ document, onClose, onDelete }: DocumentDetailProps) {
  const { data: events, loading: eventsLoading } = useApi<LabEvent[]>(
    () => getDocumentEvents(document.id),
    [document.id],
  );

  const { data: unmapped, loading: unmappedLoading } = useApi<UnmappedRow[]>(
    () => getDocumentUnmappedRows(document.id),
    [document.id],
  );

  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const groupedEvents = useMemo(() => {
    return events ? groupEventsByCategory(events) : new Map();
  }, [events]);

  const handleDelete = async () => {
    if (!confirm(`Delete "${document.filename}"? This cannot be undone.`)) {
      return;
    }

    setDeleting(true);
    setDeleteError(null);

    try {
      await deleteDocument(document.id);
      onDelete();
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Failed to delete");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {document.filename}
          </h3>
          <p className="text-sm text-gray-500">
            Uploaded {formatDate(document.uploaded_at)} · {document.page_count}{" "}
            pages
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-md border border-red-200 disabled:opacity-50"
          >
            {deleting ? "Deleting..." : "🗑️ Delete"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1"
          >
            ✕
          </button>
        </div>
      </div>

      {deleteError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {deleteError}
        </div>
      )}

      {/* Events grouped by panel/category */}
      <div className="mb-6">
        <h4 className="font-medium text-gray-900 mb-3">
          Extracted Events ({events?.length ?? "..."})
        </h4>
        {eventsLoading ? (
          <p className="text-gray-500">Loading events...</p>
        ) : events && events.length > 0 ? (
          <div className="max-h-80 overflow-y-auto">
            {Array.from(groupedEvents.entries()).map(
              ([category, categoryEvents], idx) => (
                <CollapsiblePanel
                  key={category}
                  title={category}
                  count={categoryEvents.length}
                  defaultOpen={idx === 0}
                >
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-2 text-left text-gray-600">
                          Biomarker
                        </th>
                        <th className="px-3 py-2 text-left text-gray-600">
                          Value
                        </th>
                        <th className="px-3 py-2 text-left text-gray-600">
                          Unit
                        </th>
                        <th className="px-3 py-2 text-left text-gray-600">
                          Page
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {categoryEvents.map((event) => (
                        <tr key={event.event_id} className="hover:bg-gray-50">
                          <td className="px-3 py-2 font-medium">
                            {event.analyte_name || event.biomarker_id}
                          </td>
                          <td className="px-3 py-2">
                            {event.value_normalized?.toFixed(2) ??
                              event.value_original}
                          </td>
                          <td className="px-3 py-2">
                            {event.unit_canonical ?? event.unit_original}
                          </td>
                          <td className="px-3 py-2">{event.page}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CollapsiblePanel>
              ),
            )}
          </div>
        ) : (
          <p className="text-gray-500 text-sm">No events extracted</p>
        )}
      </div>

      {/* Unmapped Rows */}
      <div>
        <h4 className="font-medium text-gray-900 mb-3">
          Unmapped Rows ({unmapped?.length ?? "..."})
        </h4>
        {unmappedLoading ? (
          <p className="text-gray-500">Loading...</p>
        ) : unmapped && unmapped.length > 0 ? (
          <div className="max-h-48 overflow-y-auto border rounded-md border-yellow-200 bg-yellow-50">
            <table className="w-full text-sm">
              <thead className="bg-yellow-100 sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left text-yellow-800">Label</th>
                  <th className="px-3 py-2 text-left text-yellow-800">Value</th>
                  <th className="px-3 py-2 text-left text-yellow-800">Unit</th>
                  <th className="px-3 py-2 text-left text-yellow-800">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-yellow-200">
                {unmapped.map((row) => (
                  <tr key={row.row_id}>
                    <td className="px-3 py-2">{row.raw_label}</td>
                    <td className="px-3 py-2">{row.raw_value}</td>
                    <td className="px-3 py-2">{row.raw_unit ?? "—"}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs ${
                          row.status === "pending"
                            ? "bg-yellow-200 text-yellow-800"
                            : row.status === "resolved"
                              ? "bg-green-200 text-green-800"
                              : "bg-gray-200 text-gray-600"
                        }`}
                      >
                        {row.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-green-600 text-sm">
            ✓ All rows successfully mapped
          </p>
        )}
      </div>
    </div>
  );
}

export function DocumentsPage() {
  const { data: documents, loading, error, refetch } = useApi(listDocuments);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);

  const handleDelete = () => {
    setSelectedDoc(null);
    refetch();
  };

  if (loading) {
    return (
      <div className="text-center py-12 text-gray-500">
        Loading documents...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 mb-4">{error}</p>
        <button
          type="button"
          onClick={refetch}
          className="text-blue-600 hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Documents</h2>
        <Link
          to="/"
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          + Upload New
        </Link>
      </div>

      {documents && documents.length > 0 ? (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Document List */}
          <div className="space-y-3">
            {documents.map((doc) => (
              <button
                key={doc.id}
                type="button"
                onClick={() => setSelectedDoc(doc)}
                className={`w-full text-left p-4 rounded-lg border transition-colors ${
                  selectedDoc?.id === doc.id
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 bg-white hover:border-gray-300"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{doc.filename}</p>
                    <p className="text-sm text-gray-500">
                      {formatDate(doc.uploaded_at)} · {doc.page_count} pages
                    </p>
                  </div>
                  <span className="text-2xl">📄</span>
                </div>
              </button>
            ))}
          </div>

          {/* Document Detail */}
          <div>
            {selectedDoc ? (
              <DocumentDetail
                document={selectedDoc}
                onClose={() => setSelectedDoc(null)}
                onDelete={handleDelete}
              />
            ) : (
              <div className="bg-gray-100 rounded-lg p-8 text-center text-gray-500">
                Select a document to view details
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <p className="text-4xl mb-4">📋</p>
          <p className="text-gray-600 mb-4">No documents uploaded yet</p>
          <Link to="/" className="text-blue-600 hover:underline">
            Upload your first lab report
          </Link>
        </div>
      )}
    </div>
  );
}
