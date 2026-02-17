/**
 * Upload Screen - Camera/file picker for uploading lab documents.
 */

import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Platform,
  TextInput,
  ScrollView,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import * as ImagePicker from "expo-image-picker";
import * as DocumentPicker from "expo-document-picker";
import { useDocuments } from "../hooks";
import type { RootStackParamList } from "../types";

type NavigationProp = NativeStackNavigationProp<RootStackParamList, "Upload">;

export function UploadScreen() {
  const navigation = useNavigation<NavigationProp>();
  const { uploadDocument, loading, error } = useDocuments();

  const [selectedFile, setSelectedFile] = useState<{
    uri: string;
    name: string;
    type: string;
  } | null>(null);
  const [collectedDate, setCollectedDate] = useState(
    new Date().toISOString().split("T")[0]
  );

  const requestCameraPermission = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== "granted") {
      Alert.alert(
        "Permission Required",
        "Camera access is needed to capture lab reports."
      );
      return false;
    }
    return true;
  };

  const handleCameraCapture = async () => {
    const hasPermission = await requestCameraPermission();
    if (!hasPermission) return;

    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.8,
        allowsEditing: false,
      });

      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        setSelectedFile({
          uri: asset.uri,
          name: `lab_report_${Date.now()}.jpg`,
          type: "image/jpeg",
        });
      }
    } catch (err) {
      Alert.alert("Error", "Failed to capture image");
    }
  };

  const handleFilePicker = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["application/pdf", "image/*"],
        copyToCacheDirectory: true,
      });

      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        setSelectedFile({
          uri: asset.uri,
          name: asset.name,
          type: asset.mimeType || "application/pdf",
        });
      }
    } catch (err) {
      Alert.alert("Error", "Failed to select document");
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      Alert.alert("No File", "Please select a file first");
      return;
    }

    if (!collectedDate) {
      Alert.alert("Date Required", "Please enter the collection date");
      return;
    }

    const result = await uploadDocument(selectedFile, collectedDate);

    if (result) {
      Alert.alert(
        "Upload Successful",
        `Extracted ${result.events_created} lab events from ${result.page_count} page(s).${
          result.unmapped_rows > 0
            ? `\n\n⚠️ ${result.unmapped_rows} rows could not be mapped.`
            : ""
        }`,
        [
          {
            text: "View Documents",
            onPress: () => navigation.navigate("DocumentList"),
          },
        ]
      );
      setSelectedFile(null);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Upload Lab Report</Text>
      <Text style={styles.subtitle}>
        Capture or select a PDF/image of your lab report
      </Text>

      {/* File Selection Buttons */}
      <View style={styles.buttonRow}>
        <TouchableOpacity
          style={styles.selectButton}
          onPress={handleCameraCapture}
        >
          <Text style={styles.buttonIcon}>📷</Text>
          <Text style={styles.buttonText}>Camera</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.selectButton} onPress={handleFilePicker}>
          <Text style={styles.buttonIcon}>📄</Text>
          <Text style={styles.buttonText}>Browse Files</Text>
        </TouchableOpacity>
      </View>

      {/* Selected File Preview */}
      {selectedFile && (
        <View style={styles.selectedFileCard}>
          <Text style={styles.selectedFileLabel}>Selected File:</Text>
          <Text style={styles.selectedFileName} numberOfLines={2}>
            {selectedFile.name}
          </Text>
          <TouchableOpacity
            style={styles.clearButton}
            onPress={() => setSelectedFile(null)}
          >
            <Text style={styles.clearButtonText}>✕ Remove</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Collection Date */}
      <View style={styles.dateSection}>
        <Text style={styles.dateLabel}>Collection Date</Text>
        <TextInput
          style={styles.dateInput}
          value={collectedDate}
          onChangeText={setCollectedDate}
          placeholder="YYYY-MM-DD"
          placeholderTextColor="#9ca3af"
        />
        <Text style={styles.dateHint}>
          The date when the lab tests were performed
        </Text>
      </View>

      {/* Error Display */}
      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>⚠️ {error}</Text>
        </View>
      )}

      {/* Upload Button */}
      <TouchableOpacity
        style={[
          styles.uploadButton,
          (!selectedFile || loading) && styles.uploadButtonDisabled,
        ]}
        onPress={handleUpload}
        disabled={!selectedFile || loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.uploadButtonText}>Upload & Extract</Text>
        )}
      </TouchableOpacity>

      {/* Info Section */}
      <View style={styles.infoSection}>
        <Text style={styles.infoTitle}>How it works</Text>
        <Text style={styles.infoText}>
          1. Capture or select your lab report PDF{"\n"}
          2. Enter the date the tests were collected{"\n"}
          3. We extract biomarker values automatically{"\n"}
          4. Review and track your health trends
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fff",
  },
  content: {
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: "#1f2937",
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: "#6b7280",
    marginBottom: 24,
  },
  buttonRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 24,
  },
  selectButton: {
    flex: 1,
    backgroundColor: "#f3f4f6",
    borderRadius: 12,
    padding: 20,
    alignItems: "center",
    borderWidth: 2,
    borderColor: "#e5e7eb",
    borderStyle: "dashed",
  },
  buttonIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  buttonText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#4b5563",
  },
  selectedFileCard: {
    backgroundColor: "#ecfdf5",
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: "#10b981",
  },
  selectedFileLabel: {
    fontSize: 12,
    color: "#047857",
    marginBottom: 4,
  },
  selectedFileName: {
    fontSize: 16,
    fontWeight: "600",
    color: "#065f46",
    marginBottom: 8,
  },
  clearButton: {
    alignSelf: "flex-start",
  },
  clearButtonText: {
    fontSize: 14,
    color: "#dc2626",
  },
  dateSection: {
    marginBottom: 24,
  },
  dateLabel: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1f2937",
    marginBottom: 8,
  },
  dateInput: {
    backgroundColor: "#f9fafb",
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: "#1f2937",
  },
  dateHint: {
    fontSize: 12,
    color: "#9ca3af",
    marginTop: 4,
  },
  errorContainer: {
    backgroundColor: "#fef2f2",
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  errorText: {
    color: "#dc2626",
    fontSize: 14,
  },
  uploadButton: {
    backgroundColor: "#2563eb",
    borderRadius: 12,
    padding: 16,
    alignItems: "center",
    marginBottom: 32,
  },
  uploadButtonDisabled: {
    backgroundColor: "#9ca3af",
  },
  uploadButtonText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "600",
  },
  infoSection: {
    backgroundColor: "#f9fafb",
    borderRadius: 12,
    padding: 16,
  },
  infoTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "#6b7280",
    marginBottom: 8,
  },
  infoText: {
    fontSize: 14,
    color: "#6b7280",
    lineHeight: 22,
  },
});
