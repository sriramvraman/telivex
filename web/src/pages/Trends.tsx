import type React from "react";
import { useState } from "react";
import {
  getTrend,
  listAvailableTrends,
  listTrendCategories,
} from "../api/client";
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

function getFlagBadge(flag: "H" | "L" | null): React.ReactNode {
  if (flag === "H")
    return (
      <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full font-bold text-white bg-red-500">
        H
      </span>
    );
  if (flag === "L")
    return (
      <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full font-bold text-white bg-orange-500">
        L
      </span>
    );
  return null;
}

function getDotColor(flag: "H" | "L" | null): string {
  if (flag === "H") return "#dc2626";
  if (flag === "L") return "#ea580c";
  return "#0d9488";
}

function TrendLineChart({
  points,
  unit,
}: {
  points: {
    event_id: string;
    collected_at: string;
    value: number;
    flag: "H" | "L" | null;
  }[];
  unit: string;
}) {
  const W = 500;
  const H = 160;
  const PAD = { top: 24, right: 40, bottom: 32, left: 50 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const values = points.map((p) => p.value);
  const vMin = Math.min(...values);
  const vMax = Math.max(...values);
  const vPad = (vMax - vMin) * 0.15 || vMax * 0.1 || 1;
  const yMin = vMin - vPad;
  const yMax = vMax + vPad;

  const toX = (i: number) =>
    PAD.left +
    (points.length === 1 ? plotW / 2 : (i / (points.length - 1)) * plotW);
  const toY = (v: number) =>
    PAD.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;

  const linePath = points
    .map(
      (p, i) =>
        `${i === 0 ? "M" : "L"}${toX(i).toFixed(1)},${toY(p.value).toFixed(1)}`,
    )
    .join(" ");

  const yTicks = [vMin, (vMin + vMax) / 2, vMax];

  return (
    <div className="bg-slate-50 rounded-xl p-4">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        role="img"
        aria-label="Trend chart"
      >
        {/* Grid lines */}
        {yTicks.map((v) => (
          <g key={v}>
            <line
              x1={PAD.left}
              y1={toY(v)}
              x2={W - PAD.right}
              y2={toY(v)}
              stroke="#e2e8f0"
              strokeDasharray="4,4"
            />
            <text
              x={PAD.left - 6}
              y={toY(v) + 3}
              textAnchor="end"
              className="fill-slate-400"
              fontSize="10"
            >
              {v % 1 === 0 ? v : v.toFixed(2)}
            </text>
          </g>
        ))}

        {/* Line */}
        {points.length > 1 && (
          <path
            d={linePath}
            fill="none"
            stroke="#0d9488"
            strokeWidth="2"
            strokeLinejoin="round"
          />
        )}

        {/* Dots + labels */}
        {points.map((p, i) => (
          <g key={p.event_id}>
            <circle
              cx={toX(i)}
              cy={toY(p.value)}
              r="5"
              fill={getDotColor(p.flag)}
              stroke="white"
              strokeWidth="2"
            />
            <text
              x={toX(i)}
              y={toY(p.value) - 10}
              textAnchor="middle"
              className="fill-slate-700"
              fontSize="10"
              fontWeight="600"
            >
              {p.value} {unit}
            </text>
            {/* X-axis date labels */}
            <text
              x={toX(i)}
              y={H - 6}
              textAnchor="middle"
              className="fill-slate-400"
              fontSize="9"
            >
              {formatDate(p.collected_at).split(" ").slice(0, 2).join(" ")}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function TrendChart({ trend }: TrendChartProps) {
  if (trend.points.length === 0) {
    return <p className="text-slate-400 text-sm">No data points</p>;
  }

  const values = trend.points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);

  return (
    <div className="space-y-4">
      {/* Reference range info */}
      {trend.reference_range && (
        <div className="bg-brand-50 border border-brand-200 rounded-xl px-4 py-2.5 text-sm">
          <span className="text-brand-700 font-medium">Reference Range: </span>
          <span className="text-brand-900">{trend.reference_range}</span>
        </div>
      )}

      {/* SVG Line/Dot Chart */}
      <TrendLineChart points={trend.points} unit={trend.canonical_unit} />

      {/* Data table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50/80 border-b border-slate-100">
              <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">
                Date
              </th>
              <th className="px-4 py-2.5 text-right text-xs font-medium text-slate-500">
                Value
              </th>
              <th className="px-4 py-2.5 text-right text-xs font-medium text-slate-500">
                Source
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {trend.points.map((point) => (
              <tr
                key={point.event_id}
                className={
                  point.flag === "H"
                    ? "bg-red-50/50 hover:bg-red-50"
                    : point.flag === "L"
                      ? "bg-orange-50/50 hover:bg-orange-50"
                      : "hover:bg-brand-50/30"
                }
              >
                <td className="px-4 py-2.5 text-slate-700">
                  {formatDate(point.collected_at)}
                </td>
                <td className="px-4 py-2.5 text-right">
                  <span
                    className={`font-semibold font-mono ${point.flag === "H" ? "text-red-600" : point.flag === "L" ? "text-orange-600" : "text-slate-900"}`}
                  >
                    {point.value}
                  </span>
                  <span className="text-xs text-slate-400 ml-1.5">
                    {point.unit}
                  </span>
                  {getFlagBadge(point.flag)}
                </td>
                <td className="px-4 py-2.5 text-right text-xs text-slate-400">
                  {point.page ? `p.${point.page}` : "\u2014"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Stats */}
      <div className="flex flex-wrap gap-3 text-sm">
        <div className="bg-slate-50 rounded-lg px-3 py-2">
          <span className="text-slate-400">Latest: </span>
          <span className="font-medium text-slate-800">
            {trend.points[trend.points.length - 1]?.value}{" "}
            {trend.canonical_unit}
          </span>
        </div>
        <div className="bg-slate-50 rounded-lg px-3 py-2">
          <span className="text-slate-400">Range: </span>
          <span className="font-medium text-slate-800">
            {min.toFixed(2)} - {max.toFixed(2)} {trend.canonical_unit}
          </span>
        </div>
        <div className="bg-slate-50 rounded-lg px-3 py-2">
          <span className="text-slate-400">Points: </span>
          <span className="font-medium text-slate-800">
            {trend.points.length}
          </span>
        </div>
        {trend.category && (
          <div className="bg-brand-50 rounded-lg px-3 py-2">
            <span className="text-brand-600">Category: </span>
            <span className="font-medium text-brand-700">{trend.category}</span>
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
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">
            {biomarkerName}
          </h3>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            {biomarkerId}
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
            aria-label="Close trend viewer"
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

      {loading && (
        <p className="text-slate-400 text-sm">Loading trend data...</p>
      )}
      {error && <p className="text-red-600 text-sm">{error}</p>}
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
    (item) => !selectedCategory || item.category === selectedCategory,
  );

  if (loading) {
    return (
      <div className="text-center py-12 text-slate-400 text-sm">
        Loading trends...
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
          className="text-brand-600 hover:text-brand-700 hover:underline text-sm font-medium"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-slate-900">Trends</h2>
        {categories && categories.length > 0 && (
          <select
            value={selectedCategory || ""}
            onChange={(e) => setSelectedCategory(e.target.value || null)}
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        )}
      </div>

      {filteredTrends && filteredTrends.length > 0 ? (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Biomarker List */}
          <div className="space-y-2">
            <h3 className="font-medium text-slate-500 text-sm mb-3">
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
                className={`w-full text-left p-3 rounded-xl border transition-colors ${
                  selectedBiomarker?.id === item.biomarker_id
                    ? "border-brand-600 bg-brand-50"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-slate-900">
                      {item.biomarker_name}
                    </p>
                    {item.category && (
                      <span className="text-xs px-1.5 py-0.5 bg-brand-50 text-brand-700 rounded mt-1 inline-block">
                        {item.category}
                      </span>
                    )}
                  </div>
                  <div className="text-right">
                    {item.latest_value !== null && (
                      <p className="text-sm font-mono text-slate-700">
                        {item.latest_value} {item.canonical_unit}
                      </p>
                    )}
                    <span className="text-xs text-slate-400">
                      {item.event_count}{" "}
                      {item.event_count === 1 ? "point" : "points"}
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
              <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-400 h-64 flex items-center justify-center">
                <div>
                  <svg
                    className="w-10 h-10 mx-auto mb-3 text-brand-300"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    role="img"
                    aria-label="Trend chart"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M3 17l6-6 4 4 8-8"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M17 7h4v4"
                    />
                  </svg>
                  <p className="text-sm">Select a biomarker to view trends</p>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <svg
            className="w-10 h-10 mx-auto mb-3 text-brand-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            role="img"
            aria-label="No trend data"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M3 3v18h18"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16l4-4 4 4 6-6"
            />
          </svg>
          <p className="text-slate-500 mb-1">No trend data available yet.</p>
          <p className="text-slate-400 text-sm">
            Upload some lab reports first.
          </p>
        </div>
      )}
    </div>
  );
}
