import { useCallback, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  deleteDocument,
  getBiomarker,
  getDocument,
  getDocumentEvents,
  getDocumentUnmappedRows,
  searchBiomarkers,
} from "../api/client";
import { useApi } from "../hooks/useApi";
import type { Biomarker, LabEvent, UnmappedRow } from "../types";

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// ── Tab navigation ──────────────────────────────────────────────

type TabId = "events" | "unmapped";

function Tabs({
  active,
  onChange,
  eventCount,
  unmappedCount,
}: {
  active: TabId;
  onChange: (tab: TabId) => void;
  eventCount: number;
  unmappedCount: number;
}) {
  const tabs: { id: TabId; label: string; count: number }[] = [
    { id: "events", label: "Mapped Events", count: eventCount },
    { id: "unmapped", label: "Unmapped Rows", count: unmappedCount },
  ];

  return (
    <div className="flex gap-1 bg-slate-100 p-1 rounded-lg w-fit">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
            active === tab.id
              ? "bg-white text-slate-900 shadow-sm"
              : "text-slate-500 hover:text-slate-700"
          }`}
        >
          {tab.label}
          <span
            className={`ml-2 px-1.5 py-0.5 rounded text-xs ${
              active === tab.id
                ? tab.id === "unmapped" && tab.count > 0
                  ? "bg-amber-100 text-amber-700"
                  : "bg-brand-100 text-brand-700"
                : "bg-slate-200 text-slate-500"
            }`}
          >
            {tab.count}
          </span>
        </button>
      ))}
    </div>
  );
}

// ── Biomarker Detail Modal ──────────────────────────────────────

function BiomarkerModal({
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

  const flagColor =
    event.flag === "H"
      ? { bg: "bg-red-50", text: "text-red-700", badge: "bg-red-500" }
      : event.flag === "L"
        ? {
            bg: "bg-orange-50",
            text: "text-orange-700",
            badge: "bg-orange-500",
          }
        : { bg: "bg-brand-50", text: "text-brand-700", badge: "" };

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      role="dialog"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      onKeyDown={(e) => e.key === "Escape" && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[80vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-start rounded-t-2xl">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">
              {event.analyte_name || event.biomarker_id}
            </h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              {event.biomarker_id}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              role="img"
              aria-label="Close"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Value card */}
          <div className={`rounded-xl p-4 ${flagColor.bg}`}>
            <div className="flex items-center justify-between mb-1">
              <p className={`text-sm font-medium ${flagColor.text}`}>
                Your Value
              </p>
              {event.flag && (
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-bold text-white ${flagColor.badge}`}
                >
                  {event.flag === "H" ? "HIGH" : "LOW"}
                </span>
              )}
            </div>
            <p className={`text-3xl font-bold ${flagColor.text}`}>
              {event.value_normalized?.toFixed(2) ?? event.value_original}
              <span className="text-base font-normal ml-2 opacity-70">
                {event.unit_canonical ?? event.unit_original}
              </span>
            </p>
            {event.value_original !== event.value_normalized && (
              <p className="text-xs opacity-60 mt-1">
                Original: {event.value_original} {event.unit_original}
              </p>
            )}
          </div>

          {loading ? (
            <div className="text-center py-4 text-slate-400 text-sm">
              Loading details...
            </div>
          ) : biomarker ? (
            <>
              {biomarker.default_reference_range_notes && (
                <div className="bg-emerald-50 rounded-xl p-4">
                  <p className="text-xs font-medium text-emerald-700 mb-1">
                    Reference Range
                  </p>
                  <p className="text-sm text-emerald-900 whitespace-pre-line">
                    {biomarker.default_reference_range_notes}
                  </p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-2.5 text-sm">
                {[
                  { label: "Specimen", value: biomarker.specimen },
                  { label: "Category", value: biomarker.category || "—" },
                  { label: "Unit", value: biomarker.canonical_unit },
                  {
                    label: "Measurement",
                    value: biomarker.measurement_property || "—",
                  },
                ].map((item) => (
                  <div key={item.label} className="bg-slate-50 rounded-lg p-3">
                    <p className="text-xs text-slate-400">{item.label}</p>
                    <p className="font-medium text-slate-800">{item.value}</p>
                  </div>
                ))}
              </div>
            </>
          ) : null}

          <div className="border-t pt-3">
            <p className="text-xs text-slate-400">
              Page {event.page} · Confidence{" "}
              {(event.confidence * 100).toFixed(0)}%
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Event Row ────────────────────────────────────────────────────

function EventRow({
  event,
  onClick,
}: {
  event: LabEvent;
  onClick: () => void;
}) {
  return (
    <tr
      className={`cursor-pointer transition-colors ${
        event.flag === "H"
          ? "bg-red-50/50 hover:bg-red-50"
          : event.flag === "L"
            ? "bg-orange-50/50 hover:bg-orange-50"
            : "hover:bg-brand-50/30"
      }`}
      onClick={onClick}
    >
      <td className="px-4 py-2.5">
        <span className="text-sm font-medium text-slate-900">
          {event.analyte_name || event.biomarker_id}
        </span>
        {event.flag && (
          <span
            className={`ml-2 text-[10px] px-1.5 py-0.5 rounded-full font-bold text-white ${
              event.flag === "H" ? "bg-red-500" : "bg-orange-500"
            }`}
          >
            {event.flag}
          </span>
        )}
      </td>
      <td className="px-4 py-2.5 text-right">
        <span
          className={`text-sm font-semibold ${
            event.flag === "H"
              ? "text-red-600"
              : event.flag === "L"
                ? "text-orange-600"
                : "text-slate-900"
          }`}
        >
          {event.value_normalized?.toFixed(2) ?? event.value_original}
        </span>
        <span className="text-xs text-slate-400 ml-1.5">
          {event.unit_canonical ?? event.unit_original}
        </span>
      </td>
      <td className="px-4 py-2.5 text-right text-xs text-slate-400 w-16">
        p.{event.page}
      </td>
    </tr>
  );
}

// ── Collapsible Category ─────────────────────────────────────────

function CategorySection({
  category,
  events,
  defaultOpen,
  onSelectEvent,
  borderColor,
}: {
  category: string;
  events: LabEvent[];
  defaultOpen: boolean;
  onSelectEvent: (e: LabEvent) => void;
  borderColor?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const abnormalCount = events.filter((e) => e.flag).length;

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 mb-2 w-full text-left group"
      >
        <svg
          className={`w-3.5 h-3.5 text-slate-400 transition-transform ${open ? "rotate-90" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          role="img"
          aria-label={open ? "Collapse" : "Expand"}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5l7 7-7 7"
          />
        </svg>
        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider group-hover:text-slate-700">
          {category}
        </h4>
        <span className="text-xs text-slate-400">({events.length})</span>
        {abnormalCount > 0 && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold text-white bg-red-500">
            {abnormalCount} abnormal
          </span>
        )}
      </button>
      {open && (
        <div
          className={`bg-white rounded-xl border ${borderColor || "border-slate-200"} overflow-hidden`}
        >
          <table className="w-full">
            <tbody className="divide-y divide-slate-100">
              {events.map((event) => (
                <EventRow
                  key={event.event_id}
                  event={event}
                  onClick={() => onSelectEvent(event)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Events Tab ──────────────────────────────────────────────────

function EventsTab({ events }: { events: LabEvent[] }) {
  const [selectedEvent, setSelectedEvent] = useState<LabEvent | null>(null);

  const abnormalEvents = useMemo(() => events.filter((e) => e.flag), [events]);

  const grouped = useMemo(() => {
    const groups = new Map<string, LabEvent[]>();
    for (const event of events) {
      const cat = event.category || "Other";
      if (!groups.has(cat)) groups.set(cat, []);
      groups.get(cat)?.push(event);
    }
    return groups;
  }, [events]);

  if (events.length === 0) {
    return (
      <div className="py-12 text-center text-slate-400 text-sm">
        No events extracted from this document.
      </div>
    );
  }

  return (
    <>
      <div className="space-y-4">
        {/* Abnormal markers section at top */}
        {abnormalEvents.length > 0 && (
          <CategorySection
            category="Abnormal Values"
            events={abnormalEvents}
            defaultOpen={true}
            onSelectEvent={setSelectedEvent}
            borderColor="border-red-200"
          />
        )}

        {/* Regular categories */}
        {Array.from(grouped.entries()).map(([category, categoryEvents]) => (
          <CategorySection
            key={category}
            category={category}
            events={categoryEvents}
            defaultOpen={grouped.size <= 3}
            onSelectEvent={setSelectedEvent}
          />
        ))}
      </div>

      {selectedEvent && (
        <BiomarkerModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </>
  );
}

// ── Unmapped Tab ────────────────────────────────────────────────

function UnmappedTab({
  rows,
  documentId,
  onResolved,
}: {
  rows: UnmappedRow[];
  documentId: string;
  onResolved: () => void;
}) {
  const [mappingRowId, setMappingRowId] = useState<string | null>(null);

  const pendingRows = rows.filter((r) => r.status === "pending");
  const resolvedRows = rows.filter((r) => r.status !== "pending");

  if (rows.length === 0) {
    return (
      <div className="py-12 text-center">
        <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-3">
          <svg
            className="w-5 h-5 text-emerald-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            role="img"
            aria-label="All mapped"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <p className="text-sm text-slate-500">All rows successfully mapped</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {pendingRows.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-amber-600 uppercase tracking-wider mb-2">
            Pending Review ({pendingRows.length})
          </h4>
          <div className="bg-white rounded-xl border border-amber-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-amber-50/50 border-b border-amber-100">
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-amber-700">
                    Label
                  </th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-amber-700">
                    Value
                  </th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-amber-700">
                    Unit
                  </th>
                  <th className="text-right px-4 py-2.5 text-xs font-medium text-amber-700">
                    Page
                  </th>
                  <th className="text-right px-4 py-2.5 text-xs font-medium text-amber-700">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-amber-100">
                {pendingRows.map((row) => (
                  <tr key={row.row_id} className="hover:bg-amber-50/30">
                    <td className="px-4 py-2.5 font-medium text-slate-900">
                      {row.raw_label}
                    </td>
                    <td className="px-4 py-2.5 text-slate-600">
                      {row.raw_value}
                    </td>
                    <td className="px-4 py-2.5 text-slate-500">
                      {row.raw_unit || "—"}
                    </td>
                    <td className="px-4 py-2.5 text-slate-400 text-right">
                      {row.page}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setMappingRowId(row.row_id)}
                          className="text-xs font-medium text-brand-600 hover:text-brand-700"
                        >
                          Map
                        </button>
                        <button
                          type="button"
                          onClick={async () => {
                            await fetch(
                              `/api/v1/documents/${documentId}/unmapped/${row.row_id}/ignore`,
                              { method: "POST" },
                            );
                            onResolved();
                          }}
                          className="text-xs text-slate-400 hover:text-slate-600"
                        >
                          Ignore
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {resolvedRows.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Resolved ({resolvedRows.length})
          </h4>
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <table className="w-full text-sm">
              <tbody className="divide-y divide-slate-100">
                {resolvedRows.map((row) => (
                  <tr key={row.row_id} className="text-slate-400">
                    <td className="px-4 py-2">{row.raw_label}</td>
                    <td className="px-4 py-2">{row.raw_value}</td>
                    <td className="px-4 py-2">{row.raw_unit || "—"}</td>
                    <td className="px-4 py-2 text-right">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          row.status === "resolved"
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-slate-100 text-slate-500"
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
        </div>
      )}

      {mappingRowId && (
        <MappingModal
          rowId={mappingRowId}
          documentId={documentId}
          row={rows.find((r) => r.row_id === mappingRowId) as UnmappedRow}
          onClose={() => setMappingRowId(null)}
          onMapped={() => {
            setMappingRowId(null);
            onResolved();
          }}
        />
      )}
    </div>
  );
}

// ── Mapping Modal ───────────────────────────────────────────────

function MappingModal({
  rowId,
  documentId,
  row,
  onClose,
  onMapped,
}: {
  rowId: string;
  documentId: string;
  row: UnmappedRow;
  onClose: () => void;
  onMapped: () => void;
}) {
  const [query, setQuery] = useState(row.raw_label);
  const [results, setResults] = useState<Biomarker[]>([]);
  const [searching, setSearching] = useState(false);
  const [mapping, setMapping] = useState(false);

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      return;
    }
    setSearching(true);
    try {
      const data = await searchBiomarkers(q);
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  const handleMap = async (biomarkerId: string) => {
    setMapping(true);
    try {
      const resp = await fetch(
        `/api/v1/documents/${documentId}/unmapped/${rowId}/resolve?biomarker_id=${encodeURIComponent(biomarkerId)}`,
        { method: "POST" },
      );
      if (resp.ok) {
        onMapped();
      }
    } finally {
      setMapping(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      role="dialog"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      onKeyDown={(e) => e.key === "Escape" && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[80vh] flex flex-col">
        <div className="px-6 py-4 border-b">
          <h3 className="font-semibold text-slate-900">Map to Biomarker</h3>
          <p className="text-sm text-slate-500 mt-0.5">
            "{row.raw_label}" — {row.raw_value} {row.raw_unit || ""}
          </p>
        </div>

        <div className="p-4 border-b">
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search biomarkers..."
              className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
            <button
              type="button"
              onClick={() => doSearch(query)}
              disabled={searching}
              className="px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors"
            >
              Search
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2 min-h-[200px] max-h-[400px]">
          {searching ? (
            <div className="text-center py-8 text-slate-400 text-sm">
              Searching...
            </div>
          ) : results.length > 0 ? (
            <div className="space-y-1">
              {results.map((b) => (
                <button
                  key={b.biomarker_id}
                  type="button"
                  onClick={() => handleMap(b.biomarker_id)}
                  disabled={mapping}
                  className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-brand-50 transition-colors disabled:opacity-50"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-900">
                        {b.analyte_name}
                      </p>
                      <p className="text-xs text-slate-400 font-mono">
                        {b.biomarker_id} · {b.canonical_unit}
                      </p>
                    </div>
                    <span className="text-xs text-brand-600 font-medium">
                      Select
                    </span>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-400 text-sm">
              {query.length > 1
                ? "No results. Try a different search."
                : "Type a name and click Search."}
            </div>
          )}
        </div>

        <div className="px-6 py-3 border-t flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-sm text-slate-500 hover:text-slate-700"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────

export function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabId>("events");
  const [deleting, setDeleting] = useState(false);

  const documentId = id as string;

  const { data: document, loading: docLoading } = useApi(
    () => getDocument(documentId),
    [documentId],
  );

  const {
    data: events,
    loading: eventsLoading,
    refetch: refetchEvents,
  } = useApi<LabEvent[]>(() => getDocumentEvents(documentId), [documentId]);

  const {
    data: unmapped,
    loading: unmappedLoading,
    refetch: refetchUnmapped,
  } = useApi<UnmappedRow[]>(
    () => getDocumentUnmappedRows(documentId),
    [documentId],
  );

  const handleDelete = async () => {
    if (
      !window.confirm(`Delete "${document?.filename}"? This cannot be undone.`)
    ) {
      return;
    }
    setDeleting(true);
    try {
      await deleteDocument(documentId);
      navigate("/documents");
    } finally {
      setDeleting(false);
    }
  };

  const handleResolved = () => {
    refetchEvents();
    refetchUnmapped();
  };

  if (docLoading) {
    return <div className="text-center py-16 text-slate-400">Loading...</div>;
  }

  if (!document) {
    return (
      <div className="text-center py-16">
        <p className="text-slate-500 mb-3">Document not found</p>
        <Link
          to="/documents"
          className="text-brand-600 hover:underline text-sm"
        >
          Back to documents
        </Link>
      </div>
    );
  }

  return (
    <div>
      {/* Breadcrumb + header */}
      <div className="mb-6">
        <Link
          to="/documents"
          className="text-sm text-slate-400 hover:text-slate-600 transition-colors"
        >
          Documents
        </Link>
        <span className="text-slate-300 mx-2">/</span>
        <span className="text-sm text-slate-600">{document.filename}</span>
      </div>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">
            {document.filename}
          </h2>
          <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-sm text-slate-500 mt-0.5">
            {document.collected_at && (
              <span>Collected {formatDate(document.collected_at)}</span>
            )}
            {document.reported_at && (
              <span>Reported {formatDate(document.reported_at)}</span>
            )}
            <span>Uploaded {formatDate(document.uploaded_at)}</span>
            <span>{document.page_count} pages</span>
          </div>
        </div>
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleting}
          className="px-3 py-1.5 text-sm text-red-500 hover:text-red-600 hover:bg-red-50 rounded-lg border border-red-200 disabled:opacity-50 transition-colors"
        >
          {deleting ? "Deleting..." : "Delete"}
        </button>
      </div>

      {/* Tabs */}
      <div className="mb-5">
        <Tabs
          active={activeTab}
          onChange={setActiveTab}
          eventCount={events?.length ?? 0}
          unmappedCount={
            unmapped?.filter((r) => r.status === "pending").length ?? 0
          }
        />
      </div>

      {/* Content */}
      {activeTab === "events" ? (
        eventsLoading ? (
          <div className="text-center py-12 text-slate-400 text-sm">
            Loading events...
          </div>
        ) : (
          <EventsTab events={events ?? []} />
        )
      ) : unmappedLoading ? (
        <div className="text-center py-12 text-slate-400 text-sm">
          Loading...
        </div>
      ) : (
        <UnmappedTab
          rows={unmapped ?? []}
          documentId={documentId}
          onResolved={handleResolved}
        />
      )}
    </div>
  );
}
