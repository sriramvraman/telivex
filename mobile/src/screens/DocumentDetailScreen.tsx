/**
 * Document Detail Screen - Shows extracted events grouped by panel and unmapped rows.
 * Supports document deletion and biomarker detail viewing.
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
  Modal,
} from "react-native";
import { useRoute, useNavigation } from "@react-navigation/native";
import type { RouteProp } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { apiClient } from "../api/client";
import type {
  RootStackParamList,
  LabEventResponse,
  UnmappedRowResponse,
  BiomarkerResponse,
} from "../types";

type RouteProps = RouteProp<RootStackParamList, "DocumentDetail">;
type NavigationProp = NativeStackNavigationProp<
  RootStackParamList,
  "DocumentDetail"
>;

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

/** Biomarker Detail Modal */
function BiomarkerDetailModal({
  event,
  onClose,
}: {
  event: LabEventResponse;
  onClose: () => void;
}) {
  const [biomarker, setBiomarker] = useState<BiomarkerResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchBiomarker = async () => {
      try {
        const data = await apiClient.getBiomarker(event.biomarker_id);
        setBiomarker(data);
      } catch (err) {
        console.error("Failed to fetch biomarker:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchBiomarker();
  }, [event.biomarker_id]);

  return (
    <Modal
      visible
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <View style={modalStyles.container}>
        {/* Header */}
        <View style={modalStyles.header}>
          <View>
            <Text style={modalStyles.title}>{event.analyte_name}</Text>
            <Text style={modalStyles.subtitle}>{event.biomarker_id}</Text>
          </View>
          <TouchableOpacity onPress={onClose} style={modalStyles.closeButton}>
            <Text style={modalStyles.closeButtonText}>✕</Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={modalStyles.content}>
          {/* Current Value */}
          <View style={modalStyles.valueCard}>
            <Text style={modalStyles.valueLabel}>Your Value</Text>
            <View style={modalStyles.valueRow}>
              <Text style={modalStyles.valueNumber}>
                {event.value_normalized.toFixed(2)}
              </Text>
              <Text style={modalStyles.valueUnit}>{event.unit_canonical}</Text>
            </View>
            {event.value_original !== event.value_normalized && (
              <Text style={modalStyles.originalValue}>
                Original: {event.value_original} {event.unit_original}
              </Text>
            )}
          </View>

          {loading ? (
            <View style={modalStyles.loadingContainer}>
              <ActivityIndicator size="small" color="#2563eb" />
              <Text style={modalStyles.loadingText}>Loading details...</Text>
            </View>
          ) : biomarker ? (
            <>
              {/* Reference Range */}
              {biomarker.default_reference_range_notes && (
                <View style={modalStyles.referenceCard}>
                  <Text style={modalStyles.referenceLabel}>
                    📊 Reference Range
                  </Text>
                  <Text style={modalStyles.referenceText}>
                    {biomarker.default_reference_range_notes}
                  </Text>
                </View>
              )}

              {/* Biomarker Info */}
              <View style={modalStyles.section}>
                <Text style={modalStyles.sectionTitle}>Biomarker Details</Text>
                <View style={modalStyles.infoGrid}>
                  <View style={modalStyles.infoItem}>
                    <Text style={modalStyles.infoLabel}>Specimen</Text>
                    <Text style={modalStyles.infoValue}>
                      {biomarker.specimen}
                    </Text>
                  </View>
                  <View style={modalStyles.infoItem}>
                    <Text style={modalStyles.infoLabel}>Category</Text>
                    <Text style={modalStyles.infoValue}>
                      {biomarker.category || "—"}
                    </Text>
                  </View>
                  <View style={modalStyles.infoItem}>
                    <Text style={modalStyles.infoLabel}>Canonical Unit</Text>
                    <Text style={modalStyles.infoValue}>
                      {biomarker.canonical_unit}
                    </Text>
                  </View>
                  <View style={modalStyles.infoItem}>
                    <Text style={modalStyles.infoLabel}>Measurement</Text>
                    <Text style={modalStyles.infoValue}>
                      {biomarker.measurement_property || "—"}
                    </Text>
                  </View>
                </View>

                {biomarker.aliases && biomarker.aliases.length > 0 && (
                  <View style={modalStyles.aliasesContainer}>
                    <Text style={modalStyles.aliasesLabel}>Also known as</Text>
                    <View style={modalStyles.aliasesList}>
                      {biomarker.aliases.map((alias) => (
                        <View key={alias} style={modalStyles.aliasBadge}>
                          <Text style={modalStyles.aliasText}>{alias}</Text>
                        </View>
                      ))}
                    </View>
                  </View>
                )}
              </View>
            </>
          ) : (
            <Text style={modalStyles.errorText}>
              Biomarker details not available
            </Text>
          )}

          {/* Provenance */}
          <View style={modalStyles.provenance}>
            <Text style={modalStyles.provenanceText}>
              Source: Page {event.page ?? "?"} · Confidence:{" "}
              {(event.confidence * 100).toFixed(0)}%
            </Text>
          </View>
        </ScrollView>
      </View>
    </Modal>
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
  const [selectedEvent, setSelectedEvent] = useState<LabEventResponse | null>(
    null,
  );

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
        setError(
          err instanceof Error ? err.message : "Failed to load document",
        );
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
                err instanceof Error
                  ? err.message
                  : "Failed to delete document",
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

      {/* Hint */}
      {activeTab === "events" && events.length > 0 && (
        <Text style={styles.hintText}>
          Tap a parameter to view details and reference range
        </Text>
      )}

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
                    <TouchableOpacity
                      key={event.event_id}
                      style={styles.eventCard}
                      onPress={() => setSelectedEvent(event)}
                      activeOpacity={0.7}
                    >
                      <View style={styles.eventHeader}>
                        <Text style={styles.analyteName}>
                          {event.analyte_name}
                        </Text>
                        <Text style={styles.confidence}>
                          {(event.confidence * 100).toFixed(0)}%
                        </Text>
                      </View>
                      <View style={styles.eventBody}>
                        <Text style={styles.value}>
                          {event.value_normalized.toFixed(2)}{" "}
                          <Text style={styles.unit}>{event.unit_canonical}</Text>
                        </Text>
                        <Text style={styles.meta}>
                          Page {event.page ?? "?"} · Tap for details
                        </Text>
                      </View>
                    </TouchableOpacity>
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

      {/* Biomarker Detail Modal */}
      {selectedEvent && (
        <BiomarkerDetailModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
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
  hintText: {
    fontSize: 12,
    color: "#9ca3af",
    textAlign: "center",
    paddingVertical: 8,
    backgroundColor: "#fff",
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
    borderWidth: 1,
    borderColor: "transparent",
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
  value: {
    fontSize: 16,
    fontWeight: "700",
    color: "#2563eb",
  },
  unit: {
    fontSize: 13,
    fontWeight: "400",
    color: "#6b7280",
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

const modalStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fff",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
  },
  title: {
    fontSize: 20,
    fontWeight: "700",
    color: "#1f2937",
  },
  subtitle: {
    fontSize: 13,
    color: "#6b7280",
    marginTop: 2,
  },
  closeButton: {
    padding: 8,
  },
  closeButtonText: {
    fontSize: 20,
    color: "#6b7280",
  },
  content: {
    flex: 1,
    padding: 20,
  },
  valueCard: {
    backgroundColor: "#eff6ff",
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
  },
  valueLabel: {
    fontSize: 14,
    color: "#2563eb",
    fontWeight: "600",
    marginBottom: 8,
  },
  valueRow: {
    flexDirection: "row",
    alignItems: "baseline",
    gap: 8,
  },
  valueNumber: {
    fontSize: 36,
    fontWeight: "700",
    color: "#1e40af",
  },
  valueUnit: {
    fontSize: 18,
    color: "#3b82f6",
  },
  originalValue: {
    fontSize: 13,
    color: "#60a5fa",
    marginTop: 8,
  },
  referenceCard: {
    backgroundColor: "#f0fdf4",
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
  },
  referenceLabel: {
    fontSize: 14,
    color: "#15803d",
    fontWeight: "600",
    marginBottom: 8,
  },
  referenceText: {
    fontSize: 15,
    color: "#166534",
    lineHeight: 22,
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1f2937",
    marginBottom: 12,
  },
  infoGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  infoItem: {
    backgroundColor: "#f9fafb",
    borderRadius: 8,
    padding: 12,
    width: "48%",
  },
  infoLabel: {
    fontSize: 12,
    color: "#6b7280",
    marginBottom: 4,
  },
  infoValue: {
    fontSize: 14,
    fontWeight: "600",
    color: "#1f2937",
  },
  aliasesContainer: {
    backgroundColor: "#f9fafb",
    borderRadius: 8,
    padding: 12,
    marginTop: 10,
  },
  aliasesLabel: {
    fontSize: 12,
    color: "#6b7280",
    marginBottom: 8,
  },
  aliasesList: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
  },
  aliasBadge: {
    backgroundColor: "#e5e7eb",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  aliasText: {
    fontSize: 12,
    color: "#4b5563",
  },
  loadingContainer: {
    alignItems: "center",
    padding: 30,
  },
  loadingText: {
    fontSize: 14,
    color: "#6b7280",
    marginTop: 8,
  },
  errorText: {
    fontSize: 14,
    color: "#6b7280",
    textAlign: "center",
    padding: 20,
  },
  provenance: {
    borderTopWidth: 1,
    borderTopColor: "#e5e7eb",
    paddingTop: 16,
    marginTop: 10,
  },
  provenanceText: {
    fontSize: 12,
    color: "#9ca3af",
    textAlign: "center",
  },
});
