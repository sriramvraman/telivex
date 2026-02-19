import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  deleteDocument,
  getBiomarker,
  getDocumentEvents,
  getDocumentUnmappedRows,
  listDocuments,
} from "../api/client";
import { useApi } from "../hooks/useApi";
import type { Biomarker, Document, LabEvent, UnmappedRow } from "../types";

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Group events by category */
function groupEventsByCategory(events: LabEvent[]): Map<string, LabEvent[]> {
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

/** Biomarker detail modal */
function BiomarkerDetailModal({
  event,
  onClose,
}: {
  event: LabEvent;
  onClose: () => void;
}) {
  const { data: biomarker, loading } = useApi<Biomarker>(
    () => getBiomarker(event.biomarker_id),
    [event.biomarker_id],
  );

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full max-h-[80vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-start">
          <div>
            <h3 className="text-lg font-bold text-gray-900">
              {event.analyte_name || event.biomarker_id}
            </h3>
            <p className="text-sm text-gray-500">{event.biomarker_id}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl p-1"
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Current Value */}
          <div className={`rounded-lg p-4 ${
            event.flag
              ? event.flag === "H"
                ? "bg-red-50"
                : "bg-orange-50"
              : "bg-blue-50"
          }`}>
            <div className="flex items-center justify-between mb-1">
              <p className={`text-sm font-medium ${
                event.flag
                  ? event.flag === "H"
                    ? "text-red-600"
                    : "text-orange-600"
                  : "text-blue-600"
              }`}>
                Your Value
              </p>
              {event.flag && (
                <span className={`text-xs px-2 py-1 rounded font-bold ${
                  event.flag === "H"
                    ? "bg-red-500 text-white"
                    : "bg-orange-500 text-white"
                }`}>
                  {event.flag === "H" ? "↑ HIGH" : "↓ LOW"}
                </span>
              )}
            </div>
            <p className={`text-3xl font-bold ${
              event.flag
                ? event.flag === "H"
                  ? "text-red-700"
                  : "text-orange-700"
                : "text-blue-700"
            }`}>
              {event.value_normalized?.toFixed(2) ?? event.value_original}
              <span className="text-lg font-normal ml-2">
                {event.unit_canonical ?? event.unit_original}
              </span>
            </p>
            {event.value_original !== event.value_normalized && (
              <p className={`text-sm mt-1 ${
                event.flag
                  ? event.flag === "H"
                    ? "text-red-500"
                    : "text-orange-500"
                  : "text-blue-500"
              }`}>
                Original: {event.value_original} {event.unit_original}
              </p>
            )}
          </div>

          {loading ? (
            <div className="text-center py-4 text-gray-500">
              Loading biomarker details...
            </div>
          ) : biomarker ? (
            <>
              {/* Reference Range */}
              {biomarker.default_reference_range_notes && (
                <div className="bg-green-50 rounded-lg p-4">
                  <p className="text-sm text-green-700 font-medium mb-1">
                    📊 Reference Range
                  </p>
                  <p className="text-gray-800 whitespace-pre-line">
                    {biomarker.default_reference_range_notes}
                  </p>
                </div>
              )}

              {/* Biomarker Info */}
              <div className="space-y-3">
                <h4 className="font-medium text-gray-900">Biomarker Details</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="bg-gray-50 rounded p-3">
                    <p className="text-gray-500">Specimen</p>
                    <p className="font-medium text-gray-900">
                      {biomarker.specimen}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded p-3">
                    <p className="text-gray-500">Category</p>
                    <p className="font-medium text-gray-900">
                      {biomarker.category || "—"}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded p-3">
                    <p className="text-gray-500">Canonical Unit</p>
                    <p className="font-medium text-gray-900">
                      {biomarker.canonical_unit}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded p-3">
                    <p className="text-gray-500">Measurement</p>
                    <p className="font-medium text-gray-900">
                      {biomarker.measurement_property || "—"}
                    </p>
                  </div>
                </div>

                {biomarker.aliases && biomarker.aliases.length > 0 && (
                  <div className="bg-gray-50 rounded p-3">
                    <p className="text-gray-500 text-sm mb-1">Also known as</p>
                    <div className="flex flex-wrap gap-1">
                      {biomarker.aliases.map((alias) => (
                        <span
                          key={alias}
                          className="bg-gray-200 text-gray-700 px-2 py-0.5 rounded text-xs"
                        >
                          {alias}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <p className="text-gray-500 text-sm">
              Biomarker details not available
            </p>
          )}

          {/* Provenance */}
          <div className="border-t pt-4">
            <p className="text-xs text-gray-400">
              Source: Page {event.page} · Confidence:{" "}
              {(event.confidence * 100).toFixed(0)}%
            </p>
          </div>
        </div>
      </div>
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
  const [selectedEvent, setSelectedEvent] = useState<LabEvent | null>(null);

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
        <p className="text-xs text-gray-500 mb-2">
          Click on a parameter to see details and reference range
        </p>
        {eventsLoading ? (
          <p className="text-gray-500">Loading events...</p>
        ) : events && events.length > 0 ? (
          <div className="max-h-80 overflow-y-auto">
            {Array.from(groupedEvents.entries()).map(
              ([category, categoryEvents]: [string, LabEvent[]], idx) => (
                <CollapsiblePanel
                  key={category}
                  title={category}
                  count={categoryEvents.length}
                  defaultOpen={idx === 0}
                >
                  <div className="space-y-2">
                    {categoryEvents.map((event) => (
                      <button
                        key={event.event_id}
                        type="button"
                        onClick={() => setSelectedEvent(event)}
                        className={`w-full text-left p-3 rounded-lg hover:border-blue-200 border transition-colors ${
                          event.flag
                            ? event.flag === "H"
                              ? "bg-red-50 border-red-200"
                              : "bg-orange-50 border-orange-200"
                            : "bg-gray-50 border-transparent hover:bg-blue-50"
                        }`}
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-medium text-gray-900 flex items-center gap-2">
                            {event.analyte_name || event.biomarker_id}
                            {event.flag && (
                              <span
                                className={`text-xs px-1.5 py-0.5 rounded font-bold ${
                                  event.flag === "H"
                                    ? "bg-red-500 text-white"
                                    : "bg-orange-500 text-white"
                                }`}
                              >
                                {event.flag === "H" ? "↑ HIGH" : "↓ LOW"}
                              </span>
                            )}
                          </span>
                          <span className={`font-semibold ${
                            event.flag
                              ? event.flag === "H"
                                ? "text-red-600"
                                : "text-orange-600"
                              : "text-blue-600"
                          }`}>
                            {event.value_normalized?.toFixed(2) ??
                              event.value_original}{" "}
                            <span className="text-gray-500 font-normal text-sm">
                              {event.unit_canonical ?? event.unit_original}
                            </span>
                          </span>
                        </div>
                        <p className="text-xs text-gray-400 mt-1">
                          Page {event.page} · Tap for details
                        </p>
                      </button>
                    ))}
                  </div>
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

      {/* Biomarker Detail Modal */}
      {selectedEvent && (
        <BiomarkerDetailModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
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
