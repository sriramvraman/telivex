/**
 * Trend Viewer Screen - Displays biomarker trends over time with charts.
 */

import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
  ActivityIndicator,
} from "react-native";
import { LineChart } from "react-native-chart-kit";
import { useTrends } from "../hooks";
import type { BiomarkerTrend, TrendDataPoint } from "../types";

const screenWidth = Dimensions.get("window").width;

interface TrendCardProps {
  trend: BiomarkerTrend;
  onPress?: () => void;
}

function TrendCard({ trend, onPress }: TrendCardProps) {
  const dataPoints = trend.data_points;

  if (dataPoints.length === 0) {
    return null;
  }

  // Sort by date
  const sortedPoints = [...dataPoints].sort(
    (a, b) => new Date(a.collected_at).getTime() - new Date(b.collected_at).getTime()
  );

  // Prepare chart data
  const labels = sortedPoints.map((p) => {
    const date = new Date(p.collected_at);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  });

  const values = sortedPoints.map((p) => p.value);
  const latestValue = values[values.length - 1];
  const previousValue = values.length > 1 ? values[values.length - 2] : null;

  // Calculate trend direction
  let trendDirection = "→";
  let trendColor = "#6b7280";
  if (previousValue !== null) {
    if (latestValue > previousValue) {
      trendDirection = "↑";
      trendColor = "#dc2626"; // May need context - some biomarkers up is good
    } else if (latestValue < previousValue) {
      trendDirection = "↓";
      trendColor = "#16a34a";
    }
  }

  const chartData = {
    labels: labels.length > 5 ? labels.slice(-5) : labels,
    datasets: [
      {
        data: values.length > 5 ? values.slice(-5) : values,
        strokeWidth: 2,
      },
    ],
  };

  return (
    <TouchableOpacity style={styles.trendCard} onPress={onPress}>
      <View style={styles.trendHeader}>
        <View>
          <Text style={styles.analyteName}>{trend.analyte_name}</Text>
          <Text style={styles.biomarkerId}>{trend.biomarker_id}</Text>
        </View>
        <View style={styles.valueContainer}>
          <Text style={styles.latestValue}>{latestValue.toFixed(2)}</Text>
          <Text style={styles.unit}>{trend.unit}</Text>
          <Text style={[styles.trendIndicator, { color: trendColor }]}>
            {trendDirection}
          </Text>
        </View>
      </View>

      {values.length >= 2 && (
        <LineChart
          data={chartData}
          width={screenWidth - 64}
          height={120}
          chartConfig={{
            backgroundColor: "#fff",
            backgroundGradientFrom: "#fff",
            backgroundGradientTo: "#fff",
            decimalPlaces: 1,
            color: (opacity = 1) => `rgba(37, 99, 235, ${opacity})`,
            labelColor: (opacity = 1) => `rgba(107, 114, 128, ${opacity})`,
            style: {
              borderRadius: 8,
            },
            propsForDots: {
              r: "4",
              strokeWidth: "2",
              stroke: "#2563eb",
            },
          }}
          bezier
          style={styles.chart}
          withInnerLines={false}
          withOuterLines={false}
        />
      )}

      <Text style={styles.dataPointCount}>
        {dataPoints.length} measurement{dataPoints.length !== 1 ? "s" : ""}
      </Text>
    </TouchableOpacity>
  );
}

export function TrendViewerScreen() {
  const { trends, loading, error, fetchAllTrends } = useTrends();
  const [mockTrends, setMockTrends] = useState<BiomarkerTrend[]>([]);

  useEffect(() => {
    fetchAllTrends();

    // Set up mock data for demonstration when API not ready
    setMockTrends([
      {
        biomarker_id: "HBA1C",
        analyte_name: "Hemoglobin A1c",
        unit: "%",
        data_points: [
          { event_id: "1", collected_at: "2025-06-15", value: 6.2, unit: "%" },
          { event_id: "2", collected_at: "2025-09-15", value: 5.9, unit: "%" },
          { event_id: "3", collected_at: "2025-12-15", value: 5.7, unit: "%" },
          { event_id: "4", collected_at: "2026-01-15", value: 5.5, unit: "%" },
        ],
      },
      {
        biomarker_id: "CHOL_TOTAL",
        analyte_name: "Total Cholesterol",
        unit: "mg/dL",
        data_points: [
          { event_id: "5", collected_at: "2025-06-15", value: 210, unit: "mg/dL" },
          { event_id: "6", collected_at: "2025-12-15", value: 195, unit: "mg/dL" },
          { event_id: "7", collected_at: "2026-01-15", value: 188, unit: "mg/dL" },
        ],
      },
      {
        biomarker_id: "CREAT",
        analyte_name: "Creatinine",
        unit: "mg/dL",
        data_points: [
          { event_id: "8", collected_at: "2025-09-15", value: 0.9, unit: "mg/dL" },
          { event_id: "9", collected_at: "2026-01-15", value: 0.95, unit: "mg/dL" },
        ],
      },
    ]);
  }, [fetchAllTrends]);

  const displayTrends = trends.length > 0 ? trends : mockTrends;

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#2563eb" />
        <Text style={styles.loadingText}>Loading trends...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Health Trends</Text>
        <Text style={styles.subtitle}>
          Track your biomarkers over time
        </Text>
      </View>

      {error && (
        <View style={styles.infoBox}>
          <Text style={styles.infoText}>
            📊 Showing sample data. Upload lab reports to see your actual trends.
          </Text>
        </View>
      )}

      {displayTrends.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No trend data yet</Text>
          <Text style={styles.emptySubtext}>
            Upload multiple lab reports to start tracking trends
          </Text>
        </View>
      ) : (
        <View style={styles.trendsContainer}>
          {displayTrends.map((trend) => (
            <TrendCard key={trend.biomarker_id} trend={trend} />
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
  infoBox: {
    backgroundColor: "#dbeafe",
    marginHorizontal: 16,
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },
  infoText: {
    color: "#1e40af",
    fontSize: 14,
  },
  trendsContainer: {
    padding: 16,
    paddingTop: 0,
  },
  trendCard: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  trendHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 12,
  },
  analyteName: {
    fontSize: 18,
    fontWeight: "600",
    color: "#1f2937",
  },
  biomarkerId: {
    fontSize: 12,
    color: "#9ca3af",
    marginTop: 2,
  },
  valueContainer: {
    alignItems: "flex-end",
    flexDirection: "row",
    gap: 4,
  },
  latestValue: {
    fontSize: 24,
    fontWeight: "700",
    color: "#2563eb",
  },
  unit: {
    fontSize: 14,
    color: "#6b7280",
    marginBottom: 2,
  },
  trendIndicator: {
    fontSize: 18,
    fontWeight: "700",
    marginLeft: 4,
  },
  chart: {
    marginVertical: 8,
    borderRadius: 8,
    marginLeft: -16,
  },
  dataPointCount: {
    fontSize: 12,
    color: "#9ca3af",
    textAlign: "right",
    marginTop: 4,
  },
  emptyContainer: {
    alignItems: "center",
    padding: 40,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: "600",
    color: "#6b7280",
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: "#9ca3af",
    textAlign: "center",
  },
});
