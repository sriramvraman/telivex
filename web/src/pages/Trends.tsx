import React, { useState } from "react";
import { getTrend, listAvailableTrends, listTrendCategories } from "../api/client";
import { useApi } from "../hooks/useApi";
import type { Trend } from "../types";

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

interface TrendChartProps {
  trend: Trend;
}

function getFlagColor(flag: "H" | "L" | null): string {
  if (flag === "H") return "bg-red-500";
  if (flag === "L") return "bg-orange-500";
  return "bg-blue-500";
}

function getFlagBadge(flag: "H" | "L" | null): React.ReactNode {
  if (flag === "H") return <span className="ml-2 px-1.5 py-0.5 text-xs bg-red-100 text-red-700 rounded">HIGH</span>;
  if (flag === "L") return <span className="ml-2 px-1.5 py-0.5 text-xs bg-orange-100 text-orange-700 rounded">LOW</span>;
  return null;
}

function TrendChart({ trend }: TrendChartProps) {
  if (trend.points.length === 0) {
    return <p className="text-gray-500">No data points</p>;
  }

  // Simple chart - show min/max and values
  const values = trend.points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  return (
    <div className="space-y-4">
      {/* Reference range info */}
      {trend.reference_range && (
        <div className="bg-blue-50 border border-blue-200 rounded px-3 py-2 text-sm">
          <span className="text-blue-700 font-medium">Reference Range: </span>
          <span className="text-blue-900">{trend.reference_range}</span>
        </div>
      )}

      {/* Simple bar visualization */}
      <div className="flex items-end gap-1 h-32 bg-gray-50 rounded p-2">
        {trend.points.map((point, idx) => {
          const height = ((point.value - min) / range) * 100 || 50;
          return (
            <div
              key={point.event_id}
              className="flex-1 flex flex-col items-center gap-1"
            >
              <div
                className={`w-full ${getFlagColor(point.flag)} rounded-t hover:opacity-80 transition-colors cursor-pointer`}
                style={{ height: `${Math.max(height, 10)}%` }}
                title={`${point.value} ${trend.canonical_unit}${point.flag ? ` (${point.flag === 'H' ? 'HIGH' : 'LOW'})` : ''}\n${formatDate(point.collected_at)}`}
              />
              {idx === 0 || idx === trend.points.length - 1 ? (
                <span className="text-xs text-gray-500 truncate w-full text-center">
                  {formatDate(point.collected_at)
                    .split(" ")
                    .slice(0, 2)
                    .join(" ")}
                </span>
              ) : null}
            </div>
          );
        })}
      </div>

      {/* Data table */}
      <div className="border rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-gray-600">Date</th>
              <th className="px-3 py-2 text-right text-gray-600">Value</th>
              <th className="px-3 py-2 text-right text-gray-600">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {trend.points.map((point) => (
              <tr key={point.event_id} className="hover:bg-gray-50">
                <td className="px-3 py-2">{formatDate(point.collected_at)}</td>
                <td className={`px-3 py-2 text-right font-mono ${point.flag === 'H' ? 'text-red-600' : point.flag === 'L' ? 'text-orange-600' : ''}`}>
                  {point.value} {point.unit}
                  {getFlagBadge(point.flag)}
                </td>
                <td className="px-3 py-2 text-right text-gray-500">
                  {point.page ? `Page ${point.page}` : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Stats */}
      <div className="flex flex-wrap gap-4 text-sm">
        <div className="bg-gray-100 rounded px-3 py-2">
          <span className="text-gray-500">Latest: </span>
          <span className="font-medium">
            {trend.points[trend.points.length - 1]?.value}{" "}
            {trend.canonical_unit}
          </span>
        </div>
        <div className="bg-gray-100 rounded px-3 py-2">
          <span className="text-gray-500">Range: </span>
          <span className="font-medium">
            {min.toFixed(2)} - {max.toFixed(2)} {trend.canonical_unit}
          </span>
        </div>
        <div className="bg-gray-100 rounded px-3 py-2">
          <span className="text-gray-500">Points: </span>
          <span className="font-medium">{trend.points.length}</span>
        </div>
        {trend.category && (
          <div className="bg-gray-100 rounded px-3 py-2">
            <span className="text-gray-500">Category: </span>
            <span className="font-medium">{trend.category}</span>
          </div>
        )}
      </div>
    </div>
  );
}

interface TrendViewerProps {
  biomarkerId: string;
  biomarkerName: string;
  onClose: () => void;
}

function TrendViewer({
  biomarkerId,
  biomarkerName,
  onClose,
}: TrendViewerProps) {
  const {
    data: trend,
    loading,
    error,
  } = useApi<Trend>(() => getTrend(biomarkerId), [biomarkerId]);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {biomarkerName}
          </h3>
          <p className="text-sm text-gray-500">{biomarkerId}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600"
        >
          ✕
        </button>
      </div>

      {loading && <p className="text-gray-500">Loading trend data...</p>}
      {error && <p className="text-red-600">{error}</p>}
      {trend && <TrendChart trend={trend} />}
    </div>
  );
}

export function TrendsPage() {
  const {
    data: availableTrends,
    loading,
    error,
    refetch,
  } = useApi(listAvailableTrends);
  const { data: categories } = useApi(listTrendCategories);
  const [selectedBiomarker, setSelectedBiomarker] = useState<{
    id: string;
    name: string;
  } | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  // Filter trends by category
  const filteredTrends = availableTrends?.filter(
    (item) => !selectedCategory || item.category === selectedCategory
  );

  if (loading) {
    return (
      <div className="text-center py-12 text-gray-500">Loading trends...</div>
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
        <h2 className="text-2xl font-bold text-gray-900">Trends</h2>
        {categories && categories.length > 0 && (
          <select
            value={selectedCategory || ""}
            onChange={(e) => setSelectedCategory(e.target.value || null)}
            className="border rounded-md px-3 py-2 text-sm"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        )}
      </div>

      {filteredTrends && filteredTrends.length > 0 ? (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Biomarker List */}
          <div className="space-y-2">
            <h3 className="font-medium text-gray-700 mb-3">
              Available Biomarkers ({filteredTrends.length})
            </h3>
            {filteredTrends.map((item) => (
              <button
                key={item.biomarker_id}
                type="button"
                onClick={() =>
                  setSelectedBiomarker({
                    id: item.biomarker_id,
                    name: item.biomarker_name,
                  })
                }
                className={`w-full text-left p-3 rounded-lg border transition-colors ${
                  selectedBiomarker?.id === item.biomarker_id
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 bg-white hover:border-gray-300"
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-gray-900">
                      {item.biomarker_name}
                    </p>
                    {item.category && (
                      <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
                        {item.category}
                      </span>
                    )}
                  </div>
                  <div className="text-right">
                    {item.latest_value !== null && (
                      <p className="text-sm font-mono text-gray-700">
                        {item.latest_value} {item.canonical_unit}
                      </p>
                    )}
                    <span className="text-xs text-gray-400">
                      {item.event_count} {item.event_count === 1 ? "point" : "points"}
                    </span>
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Trend Viewer */}
          <div className="lg:col-span-2">
            {selectedBiomarker ? (
              <TrendViewer
                biomarkerId={selectedBiomarker.id}
                biomarkerName={selectedBiomarker.name}
                onClose={() => setSelectedBiomarker(null)}
              />
            ) : (
              <div className="bg-gray-100 rounded-lg p-8 text-center text-gray-500 h-64 flex items-center justify-center">
                <div>
                  <p className="text-4xl mb-2">📈</p>
                  <p>Select a biomarker to view trends</p>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <p className="text-4xl mb-4">📊</p>
          <p className="text-gray-600 mb-4">
            No trend data available yet. Upload some lab reports first.
          </p>
        </div>
      )}
    </div>
  );
}
