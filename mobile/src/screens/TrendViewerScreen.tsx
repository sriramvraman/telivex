/**
 * Trend Viewer Screen - Displays biomarker trends over time with charts.
 */

import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { LineChart } from "react-native-chart-kit";
import { apiClient } from "../api/client";
import type { AvailableTrend, TrendResponse, TrendPoint } from "../types";

const screenWidth = Dimensions.get("window").width;

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

function getFlagColor(flag: "H" | "L" | null): string {
  if (flag === "H") return "#dc2626"; // red
  if (flag === "L") return "#f97316"; // orange
  return "#2563eb"; // blue
}

interface TrendDetailProps {
  trend: TrendResponse;
  onClose: () => void;
}

function TrendDetail({ trend, onClose }: TrendDetailProps) {
  if (trend.points.length === 0) {
    return (
      <View style={styles.detailContainer}>
        <View style={styles.detailHeader}>
          <Text style={styles.detailTitle}>{trend.analyte_name}</Text>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Text style={styles.closeButtonText}>✕</Text>
          </TouchableOpacity>
        </View>
        <Text style={styles.emptyText}>No data points</Text>
      </View>
    );
  }

  // Sort by date ascending
  const sortedPoints = [...trend.points].sort(
    (a, b) => new Date(a.collected_at).getTime() - new Date(b.collected_at).getTime()
  );

  // Prepare chart data
  const labels = sortedPoints.map((p) => formatDate(p.collected_at));
  const values = sortedPoints.map((p) => p.value);
  const latestValue = values[values.length - 1];
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);

  // Only show last 7 points in chart for readability
  const chartLabels = labels.slice(-7);
  const chartValues = values.slice(-7);

  const chartData = {
    labels: chartLabels,
    datasets: [{ data: chartValues, strokeWidth: 2 }],
  };

  return (
    <View style={styles.detailContainer}>
      <View style={styles.detailHeader}>
        <View>
          <Text style={styles.detailTitle}>{trend.analyte_name}</Text>
          {trend.category && (
            <View style={styles.categoryBadge}>
              <Text style={styles.categoryText}>{trend.category}</Text>
            </View>
          )}
        </View>
        <TouchableOpacity onPress={onClose} style={styles.closeButton}>
          <Text style={styles.closeButtonText}>✕</Text>
        </TouchableOpacity>
      </View>

      {/* Reference Range */}
      {trend.reference_range && (
        <View style={styles.referenceBox}>
          <Text style={styles.referenceLabel}>Reference Range:</Text>
          <Text style={styles.referenceValue}>{trend.reference_range}</Text>
        </View>
      )}

      {/* Chart */}
      {chartValues.length >= 2 && (
        <LineChart
          data={chartData}
          width={screenWidth - 64}
          height={150}
          chartConfig={{
            backgroundColor: "#fff",
            backgroundGradientFrom: "#fff",
            backgroundGradientTo: "#fff",
            decimalPlaces: 2,
            color: (opacity = 1) => `rgba(37, 99, 235, ${opacity})`,
            labelColor: (opacity = 1) => `rgba(107, 114, 128, ${opacity})`,
            style: { borderRadius: 8 },
            propsForDots: { r: "4", strokeWidth: "2", stroke: "#2563eb" },
          }}
          bezier
          style={styles.chart}
          withInnerLines={false}
          withOuterLines={false}
        />
      )}

      {/* Stats */}
      <View style={styles.statsRow}>
        <View style={styles.statBox}>
          <Text style={styles.statLabel}>Latest</Text>
          <Text style={styles.statValue}>
            {latestValue.toFixed(2)} {trend.canonical_unit}
          </Text>
        </View>
        <View style={styles.statBox}>
          <Text style={styles.statLabel}>Range</Text>
          <Text style={styles.statValue}>
            {minValue.toFixed(2)} - {maxValue.toFixed(2)}
          </Text>
        </View>
        <View style={styles.statBox}>
          <Text style={styles.statLabel}>Points</Text>
          <Text style={styles.statValue}>{trend.points.length}</Text>
        </View>
      </View>

      {/* Data Table */}
      <View style={styles.tableContainer}>
        <View style={styles.tableHeader}>
          <Text style={styles.tableHeaderText}>Date</Text>
          <Text style={styles.tableHeaderText}>Value</Text>
          <Text style={styles.tableHeaderText}>Source</Text>
        </View>
        {sortedPoints.slice(-10).reverse().map((point) => (
          <View key={point.event_id} style={styles.tableRow}>
            <Text style={styles.tableCell}>
              {new Date(point.collected_at).toLocaleDateString("en-IN", {
                year: "numeric",
                month: "short",
                day: "numeric",
              })}
            </Text>
            <View style={styles.valueCell}>
              <Text style={[styles.tableCell, { color: getFlagColor(point.flag) }]}>
                {point.value.toFixed(2)} {point.unit}
              </Text>
              {point.flag && (
                <View style={[styles.flagBadge, { backgroundColor: getFlagColor(point.flag) + "20" }]}>
                  <Text style={[styles.flagText, { color: getFlagColor(point.flag) }]}>
                    {point.flag === "H" ? "HIGH" : "LOW"}
                  </Text>
                </View>
              )}
            </View>
            <Text style={[styles.tableCell, styles.sourceCell]}>
              {point.page ? `Page ${point.page}` : "-"}
            </Text>
          </View>
        ))}
      </View>
    </View>
  );
}

interface TrendListItemProps {
  item: AvailableTrend;
  isSelected: boolean;
  onPress: () => void;
}

function TrendListItem({ item, isSelected, onPress }: TrendListItemProps) {
  return (
    <TouchableOpacity
      style={[styles.listItem, isSelected && styles.listItemSelected]}
      onPress={onPress}
    >
      <View style={styles.listItemLeft}>
        <Text style={styles.listItemName}>{item.biomarker_name}</Text>
        {item.category && (
          <View style={styles.categoryBadgeSmall}>
            <Text style={styles.categoryTextSmall}>{item.category}</Text>
          </View>
        )}
      </View>
      <View style={styles.listItemRight}>
        {item.latest_value !== null && (
          <Text style={styles.listItemValue}>
            {item.latest_value.toFixed(2)} {item.canonical_unit}
          </Text>
        )}
        <Text style={styles.listItemCount}>
          {item.event_count} {item.event_count === 1 ? "point" : "points"}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

export function TrendViewerScreen() {
  const [availableTrends, setAvailableTrends] = useState<AvailableTrend[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedBiomarker, setSelectedBiomarker] = useState<AvailableTrend | null>(null);
  const [trendDetail, setTrendDetail] = useState<TrendResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [trends, cats] = await Promise.all([
        apiClient.listAvailableTrends(),
        apiClient.listTrendCategories(),
      ]);
      setAvailableTrends(trends);
      setCategories(cats);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load trends");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const fetchTrendDetail = useCallback(async (biomarkerId: string) => {
    setDetailLoading(true);
    try {
      const detail = await apiClient.getBiomarkerTrend(biomarkerId);
      setTrendDetail(detail);
    } catch (err: any) {
      setError(err.message || "Failed to load trend details");
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchData();
  }, [fetchData]);

  const handleSelectBiomarker = (item: AvailableTrend) => {
    setSelectedBiomarker(item);
    fetchTrendDetail(item.biomarker_id);
  };

  const handleCloseTrend = () => {
    setSelectedBiomarker(null);
    setTrendDetail(null);
  };

  const filteredTrends = availableTrends.filter(
    (item) => !selectedCategory || item.category === selectedCategory
  );

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#2563eb" />
        <Text style={styles.loadingText}>Loading trends...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.title}>Health Trends</Text>
        <Text style={styles.subtitle}>Track your biomarkers over time</Text>
      </View>

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      {/* Category Filter */}
      {categories.length > 0 && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.categoryScroll}
          contentContainerStyle={styles.categoryContainer}
        >
          <TouchableOpacity
            style={[styles.categoryChip, !selectedCategory && styles.categoryChipActive]}
            onPress={() => setSelectedCategory(null)}
          >
            <Text style={[styles.categoryChipText, !selectedCategory && styles.categoryChipTextActive]}>
              All
            </Text>
          </TouchableOpacity>
          {categories.map((cat) => (
            <TouchableOpacity
              key={cat}
              style={[styles.categoryChip, selectedCategory === cat && styles.categoryChipActive]}
              onPress={() => setSelectedCategory(cat)}
            >
              <Text style={[styles.categoryChipText, selectedCategory === cat && styles.categoryChipTextActive]}>
                {cat}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {/* Trend Detail or List */}
      {selectedBiomarker && trendDetail ? (
        <View style={styles.detailWrapper}>
          {detailLoading ? (
            <ActivityIndicator size="large" color="#2563eb" />
          ) : (
            <TrendDetail trend={trendDetail} onClose={handleCloseTrend} />
          )}
        </View>
      ) : filteredTrends.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyEmoji}>📊</Text>
          <Text style={styles.emptyTitle}>No trend data yet</Text>
          <Text style={styles.emptySubtitle}>
            Upload lab reports to start tracking your biomarker trends
          </Text>
        </View>
      ) : (
        <View style={styles.listContainer}>
          <Text style={styles.listTitle}>
            Available Biomarkers ({filteredTrends.length})
          </Text>
          {filteredTrends.map((item) => (
            <TrendListItem
              key={item.biomarker_id}
              item={item}
              isSelected={selectedBiomarker?.biomarker_id === item.biomarker_id}
              onPress={() => handleSelectBiomarker(item)}
            />
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f5f5f5",
  },
  centerContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  loadingText: {
    marginTop: 12,
    color: "#6b7280",
    fontSize: 16,
  },
  header: {
    padding: 20,
    paddingBottom: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: "#1f2937",
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: "#6b7280",
  },
  errorBox: {
    backgroundColor: "#fee2e2",
    marginHorizontal: 16,
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },
  errorText: {
    color: "#dc2626",
    fontSize: 14,
  },
  categoryScroll: {
    marginBottom: 16,
  },
  categoryContainer: {
    paddingHorizontal: 16,
    gap: 8,
  },
  categoryChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#e5e7eb",
    marginRight: 8,
  },
  categoryChipActive: {
    backgroundColor: "#2563eb",
    borderColor: "#2563eb",
  },
  categoryChipText: {
    fontSize: 14,
    color: "#6b7280",
  },
  categoryChipTextActive: {
    color: "#fff",
  },
  listContainer: {
    padding: 16,
  },
  listTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#374151",
    marginBottom: 12,
  },
  listItem: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#e5e7eb",
  },
  listItemSelected: {
    borderColor: "#2563eb",
    backgroundColor: "#eff6ff",
  },
  listItemLeft: {
    flex: 1,
  },
  listItemName: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1f2937",
    marginBottom: 4,
  },
  listItemRight: {
    alignItems: "flex-end",
  },
  listItemValue: {
    fontSize: 14,
    fontWeight: "600",
    color: "#2563eb",
    fontFamily: "monospace",
  },
  listItemCount: {
    fontSize: 12,
    color: "#9ca3af",
    marginTop: 2,
  },
  categoryBadgeSmall: {
    backgroundColor: "#f3f4f6",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    alignSelf: "flex-start",
  },
  categoryTextSmall: {
    fontSize: 11,
    color: "#6b7280",
  },
  detailWrapper: {
    padding: 16,
  },
  detailContainer: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 16,
  },
  detailHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 16,
  },
  detailTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#1f2937",
  },
  categoryBadge: {
    backgroundColor: "#f3f4f6",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    marginTop: 4,
    alignSelf: "flex-start",
  },
  categoryText: {
    fontSize: 12,
    color: "#6b7280",
  },
  closeButton: {
    padding: 8,
  },
  closeButtonText: {
    fontSize: 20,
    color: "#9ca3af",
  },
  referenceBox: {
    backgroundColor: "#dbeafe",
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    flexDirection: "row",
    gap: 8,
  },
  referenceLabel: {
    fontSize: 14,
    color: "#1e40af",
    fontWeight: "600",
  },
  referenceValue: {
    fontSize: 14,
    color: "#1e3a8a",
  },
  chart: {
    marginVertical: 8,
    borderRadius: 8,
    marginLeft: -8,
  },
  statsRow: {
    flexDirection: "row",
    gap: 8,
    marginVertical: 16,
  },
  statBox: {
    flex: 1,
    backgroundColor: "#f9fafb",
    padding: 12,
    borderRadius: 8,
  },
  statLabel: {
    fontSize: 12,
    color: "#6b7280",
    marginBottom: 4,
  },
  statValue: {
    fontSize: 14,
    fontWeight: "600",
    color: "#1f2937",
  },
  tableContainer: {
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 8,
    overflow: "hidden",
  },
  tableHeader: {
    flexDirection: "row",
    backgroundColor: "#f9fafb",
    paddingVertical: 12,
    paddingHorizontal: 12,
  },
  tableHeaderText: {
    flex: 1,
    fontSize: 12,
    fontWeight: "600",
    color: "#6b7280",
  },
  tableRow: {
    flexDirection: "row",
    paddingVertical: 12,
    paddingHorizontal: 12,
    borderTopWidth: 1,
    borderTopColor: "#e5e7eb",
  },
  tableCell: {
    flex: 1,
    fontSize: 13,
    color: "#374151",
  },
  valueCell: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  sourceCell: {
    color: "#9ca3af",
    textAlign: "right",
  },
  flagBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  flagText: {
    fontSize: 10,
    fontWeight: "600",
  },
  emptyContainer: {
    alignItems: "center",
    padding: 40,
  },
  emptyEmoji: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#6b7280",
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    color: "#9ca3af",
    textAlign: "center",
  },
  emptyText: {
    fontSize: 16,
    color: "#6b7280",
    textAlign: "center",
    padding: 20,
  },
});
