/**
 * Reusable loading spinner component.
 */

import React from "react";
import { View, ActivityIndicator, Text, StyleSheet } from "react-native";

interface LoadingSpinnerProps {
  message?: string;
  size?: "small" | "large";
  color?: string;
}

export function LoadingSpinner({
  message,
  size = "large",
  color = "#2563eb",
}: LoadingSpinnerProps) {
  return (
    <View style={styles.container}>
      <ActivityIndicator size={size} color={color} />
      {message && <Text style={styles.message}>{message}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  message: {
    marginTop: 12,
    color: "#6b7280",
    fontSize: 16,
    textAlign: "center",
  },
});
