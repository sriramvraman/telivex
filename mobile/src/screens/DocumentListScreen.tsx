/**
 * Document List Screen - Shows all uploaded lab documents with delete option.
 */

import React, { useEffect, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from "react-native";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useDocuments } from "../hooks";
import { apiClient } from "../api/client";
import type { RootStackParamList, DocumentResponse } from "../types";

type NavigationProp = NativeStackNavigationProp<RootStackParamList, "DocumentList">;

export function DocumentListScreen() {
  const navigation = useNavigation<NavigationProp>();
  const { documents, loading, error, fetchDocuments } = useDocuments();

  // Refresh documents when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      fetchDocuments();
    }, [fetchDocuments]),
  );

  const handleDeleteDocument = async (doc: DocumentResponse) => {
    Alert.alert(
      "Delete Document",
      `Delete "${doc.filename}"? This will remove all extracted data and cannot be undone.`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            try {
              await apiClient.deleteDocument(doc.document_id);
              fetchDocuments(); // Refresh the list
            } catch (err) {
              Alert.alert(
                "Error",
                err instanceof Error ? err.message : "Failed to delete document",
              );
            }
          },
        },
      ],
    );
  };

  const renderDocument = ({ item }: { item: DocumentResponse }) => {
    const uploadDate = new Date(item.uploaded_at).toLocaleDateString();

    return (
      <TouchableOpacity
        style={styles.documentCard}
        onPress={() =>
          navigation.navigate("DocumentDetail", { documentId: item.document_id })
        }
        onLongPress={() => handleDeleteDocument(item)}
      >
        <View style={styles.documentHeader}>
          <View style={styles.documentTitleRow}>
            <Text style={styles.documentName} numberOfLines={1}>
              {item.filename}
            </Text>
            <TouchableOpacity
              style={styles.deleteIcon}
              onPress={() => handleDeleteDocument(item)}
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            >
              <Text style={styles.deleteIconText}>🗑️</Text>
            </TouchableOpacity>
          </View>
          <Text style={styles.documentDate}>{uploadDate}</Text>
        </View>

        <View style={styles.documentStats}>
          <View style={styles.stat}>
            <Text style={styles.statValue}>{item.event_count}</Text>
            <Text style={styles.statLabel}>Events</Text>
          </View>
          <View style={styles.stat}>
            <Text style={styles.statValue}>{item.page_count ?? "-"}</Text>
            <Text style={styles.statLabel}>Pages</Text>
          </View>
          {item.unmapped_count > 0 && (
            <View style={[styles.stat, styles.warningBadge]}>
              <Text style={[styles.statValue, styles.warningText]}>
                {item.unmapped_count}
              </Text>
              <Text style={[styles.statLabel, styles.warningText]}>Unmapped</Text>
            </View>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  if (loading && documents.length === 0) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#2563eb" />
        <Text style={styles.loadingText}>Loading documents...</Text>
      </View>
    );
  }

  if (error && documents.length === 0) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>⚠️ {error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={fetchDocuments}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={documents}
        renderItem={renderDocument}
        keyExtractor={(item) => item.document_id}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={fetchDocuments} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No documents yet</Text>
            <Text style={styles.emptySubtext}>
              Upload your first lab report to get started
            </Text>
          </View>
        }
        ListHeaderComponent={
          documents.length > 0 ? (
            <Text style={styles.hintText}>
              Long-press or tap 🗑️ to delete a document
            </Text>
          ) : null
        }
      />

      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate("Upload")}
      >
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>
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
    marginBottom: 16,
  },
  retryButton: {
    backgroundColor: "#2563eb",
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
  listContent: {
    padding: 16,
    paddingBottom: 100,
  },
  hintText: {
    fontSize: 12,
    color: "#9ca3af",
    textAlign: "center",
    marginBottom: 12,
  },
  documentCard: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  documentHeader: {
    marginBottom: 12,
  },
  documentTitleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  documentName: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1f2937",
    flex: 1,
    marginRight: 8,
  },
  deleteIcon: {
    padding: 4,
  },
  deleteIconText: {
    fontSize: 16,
  },
  documentDate: {
    fontSize: 14,
    color: "#6b7280",
    marginTop: 4,
  },
  documentStats: {
    flexDirection: "row",
    gap: 16,
  },
  stat: {
    alignItems: "center",
  },
  statValue: {
    fontSize: 18,
    fontWeight: "700",
    color: "#2563eb",
  },
  statLabel: {
    fontSize: 12,
    color: "#6b7280",
    marginTop: 2,
  },
  warningBadge: {
    backgroundColor: "#fef3c7",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  warningText: {
    color: "#d97706",
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
  fab: {
    position: "absolute",
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#2563eb",
    justifyContent: "center",
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    elevation: 8,
  },
  fabText: {
    color: "#fff",
    fontSize: 28,
    fontWeight: "400",
    lineHeight: 32,
  },
});
