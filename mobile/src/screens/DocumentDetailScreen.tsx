/**
 * Document Detail Screen - Shows extracted events grouped by panel and unmapped rows.
 * Supports document deletion.
 */

import React, { useEffect, useState, useMemo } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
} from "react-native";
import { useRoute, useNavigation } from "@react-navigation/native";
import type { RouteProp } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { apiClient } from "../api/client";
import type {
  RootStackParamList,
  LabEventResponse,
  UnmappedRowResponse,
} from "../types";

type RouteProps = RouteProp<RootStackParamList, "DocumentDetail">;
type NavigationProp = NativeStackNavigationProp<RootStackParamList, "DocumentDetail">;

/** Group events by category */
function groupEventsByCategory(
  events: LabEventResponse[],
): Map<string, LabEventResponse[]> {
  const groups = new Map<string, LabEventResponse[]>();
  for (const event of events) {
    const category = event.category || "Uncategorized";
    if (!groups.has(category)) {
      groups.set(category, []);
    }
    groups.get(category)!.push(event);
  }
  return groups;
}

/** Collapsible Panel Component */
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
    <View style={styles.panel}>
      <TouchableOpacity
        style={styles.panelHeader}
        onPress={() => setIsOpen(!isOpen)}
        activeOpacity={0.7}
      >
        <Text style={styles.panelTitle}>{title}</Text>
        <View style={styles.panelHeaderRight}>
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{count}</Text>
          </View>
          <Text style={[styles.chevron, isOpen && styles.chevronOpen]}>▼</Text>
        </View>
      </TouchableOpacity>
      {isOpen && <View style={styles.panelContent}>{children}</View>}
    </View>
  );
}

export function DocumentDetailScreen() {
  const route = useRoute<RouteProps>();
  const navigation = useNavigation<NavigationProp>();
  const { documentId } = route.params;

  const [events, setEvents] = useState<LabEventResponse[]>([]);
  const [unmapped, setUnmapped] = useState<UnmappedRowResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"events" | "unmapped">("events");
  const [deleting, setDeleting] = useState(false);

  const groupedEvents = useMemo(() => groupEventsByCategory(events), [events]);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [eventsData, unmappedData] = await Promise.all([
          apiClient.getDocumentEvents(documentId),
          apiClient.getUnmappedRows(documentId),
        ]);
        setEvents(eventsData);
        setUnmapped(unmappedData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load document");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [documentId]);

  const handleDelete = () => {
    Alert.alert(
      "Delete Document",
      "Are you sure you want to delete this document and all its data? This cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            setDeleting(true);
            try {
              await apiClient.deleteDocument(documentId);
              navigation.goBack();
            } catch (err) {
              Alert.alert(
                "Error",
                err instanceof Error ? err.message : "Failed to delete document",
              );
            } finally {
              setDeleting(false);
            }
          },
        },
      ],
    );
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#2563eb" />
        <Text style={styles.loadingText}>Loading events...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>⚠️ {error}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Delete Button */}
      <View style={styles.actionBar}>
        <TouchableOpacity
          style={[styles.deleteButton, deleting && styles.deleteButtonDisabled]}
          onPress={handleDelete}
          disabled={deleting}
        >
          <Text style={styles.deleteButtonText}>
            {deleting ? "Deleting..." : "🗑️ Delete Document"}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Tab Switcher */}
      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === "events" && styles.activeTab]}
          onPress={() => setActiveTab("events")}
        >
          <Text
            style={[
              styles.tabText,
              activeTab === "events" && styles.activeTabText,
            ]}
          >
            Events ({events.length})
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === "unmapped" && styles.activeTab]}
          onPress={() => setActiveTab("unmapped")}
        >
          <Text
            style={[
              styles.tabText,
              activeTab === "unmapped" && styles.activeTabText,
              unmapped.length > 0 && styles.warningText,
            ]}
          >
            Unmapped ({unmapped.length})
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content}>
        {activeTab === "events" ? (
          events.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>No events extracted</Text>
            </View>
          ) : (
            Array.from(groupedEvents.entries()).map(
              ([category, categoryEvents], idx) => (
                <CollapsiblePanel
                  key={category}
                  title={category}
                  count={categoryEvents.length}
                  defaultOpen={idx === 0}
                >
                  {categoryEvents.map((event) => (
                    <View key={event.event_id} style={styles.eventCard}>
                      <View style={styles.eventHeader}>
                        <Text style={styles.analyteName}>
                          {event.analyte_name}
                        </Text>
                        <Text style={styles.confidence}>
                          {(event.confidence * 100).toFixed(0)}%
                        </Text>
                      </View>
                      <View style={styles.eventBody}>
                        <View style={styles.valueRow}>
                          <Text style={styles.valueLabel}>Normalized:</Text>
                          <Text style={styles.value}>
                            {event.value_normalized.toFixed(2)}{" "}
                            {event.unit_canonical}
                          </Text>
                        </View>
                        <View style={styles.valueRow}>
                          <Text style={styles.valueLabel}>Original:</Text>
                          <Text style={styles.originalValue}>
                            {event.value_original} {event.unit_original}
                          </Text>
                        </View>
                        <Text style={styles.meta}>
                          Page {event.page ?? "?"}
                        </Text>
                      </View>
                    </View>
                  ))}
                </CollapsiblePanel>
              ),
            )
          )
        ) : unmapped.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>All rows mapped successfully!</Text>
            <Text style={styles.emptySubtext}>✓ No unmapped labels</Text>
          </View>
        ) : (
          unmapped.map((row) => (
            <View key={row.row_id} style={styles.unmappedCard}>
              <View style={styles.unmappedHeader}>
                <Text style={styles.unmappedLabel}>{row.raw_label}</Text>
                <View
                  style={[
                    styles.statusBadge,
                    row.status === "pending" && styles.pendingBadge,
                    row.status === "resolved" && styles.resolvedBadge,
                    row.status === "ignored" && styles.ignoredBadge,
                  ]}
                >
                  <Text style={styles.statusText}>{row.status}</Text>
                </View>
              </View>
              <View style={styles.unmappedBody}>
                <Text style={styles.unmappedValue}>
                  {row.raw_value ?? "-"} {row.raw_unit ?? ""}
                </Text>
                <Text style={styles.meta}>Page {row.page ?? "?"}</Text>
              </View>
            </View>
          ))
        )}
      </ScrollView>
    </View>
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
    padding: 20,
  },
  loadingText: {
    marginTop: 12,
    color: "#6b7280",
    fontSize: 16,
  },
  errorText: {
    color: "#dc2626",
    fontSize: 16,
    textAlign: "center",
  },
  actionBar: {
    backgroundColor: "#fff",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
  },
  deleteButton: {
    backgroundColor: "#fef2f2",
    borderWidth: 1,
    borderColor: "#fecaca",
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 16,
    alignItems: "center",
  },
  deleteButtonDisabled: {
    opacity: 0.5,
  },
  deleteButtonText: {
    color: "#dc2626",
    fontSize: 14,
    fontWeight: "600",
  },
  tabContainer: {
    flexDirection: "row",
    backgroundColor: "#fff",
    paddingHorizontal: 16,
    paddingTop: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
  },
  tab: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    marginRight: 8,
    borderBottomWidth: 2,
    borderBottomColor: "transparent",
  },
  activeTab: {
    borderBottomColor: "#2563eb",
  },
  tabText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#6b7280",
  },
  activeTabText: {
    color: "#2563eb",
  },
  warningText: {
    color: "#d97706",
  },
  content: {
    flex: 1,
    padding: 16,
  },
  panel: {
    backgroundColor: "#fff",
    borderRadius: 12,
    marginBottom: 12,
    overflow: "hidden",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  panelHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#f9fafb",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
  },
  panelTitle: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1f2937",
  },
  panelHeaderRight: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  countBadge: {
    backgroundColor: "#e5e7eb",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  countText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#6b7280",
  },
  chevron: {
    fontSize: 10,
    color: "#6b7280",
  },
  chevronOpen: {
    transform: [{ rotate: "180deg" }],
  },
  panelContent: {
    padding: 12,
    gap: 8,
  },
  eventCard: {
    backgroundColor: "#f9fafb",
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  eventHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  analyteName: {
    fontSize: 14,
    fontWeight: "600",
    color: "#1f2937",
    flex: 1,
  },
  confidence: {
    fontSize: 11,
    color: "#16a34a",
    fontWeight: "600",
    backgroundColor: "#dcfce7",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  eventBody: {
    gap: 4,
  },
  valueRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  valueLabel: {
    fontSize: 13,
    color: "#6b7280",
  },
  value: {
    fontSize: 14,
    fontWeight: "700",
    color: "#2563eb",
  },
  originalValue: {
    fontSize: 13,
    color: "#9ca3af",
  },
  meta: {
    fontSize: 11,
    color: "#9ca3af",
    marginTop: 4,
  },
  unmappedCard: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: "#f59e0b",
  },
  unmappedHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  unmappedLabel: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1f2937",
    flex: 1,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  pendingBadge: {
    backgroundColor: "#fef3c7",
  },
  resolvedBadge: {
    backgroundColor: "#dcfce7",
  },
  ignoredBadge: {
    backgroundColor: "#f3f4f6",
  },
  statusText: {
    fontSize: 12,
    fontWeight: "600",
    textTransform: "capitalize",
  },
  unmappedBody: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  unmappedValue: {
    fontSize: 14,
    color: "#6b7280",
  },
  emptyContainer: {
    alignItems: "center",
    padding: 40,
  },
  emptyText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#6b7280",
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: "#16a34a",
  },
});
