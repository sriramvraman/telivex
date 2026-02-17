/**
 * Telivex Mobile App
 * Patient-controlled longitudinal health reconstruction platform
 */

import React from "react";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Text, View, StyleSheet } from "react-native";
import type { RootStackParamList } from "./src/types";

import {
  DocumentListScreen,
  UploadScreen,
  DocumentDetailScreen,
  TrendViewerScreen,
} from "./src/screens";

// Tab Navigator for main screens
const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator<RootStackParamList>();

// Tab icon component (simple text-based for now)
function TabIcon({ name, focused }: { name: string; focused: boolean }) {
  const icons: Record<string, string> = {
    Documents: "📄",
    Trends: "📈",
    Upload: "📤",
  };

  return (
    <View style={styles.tabIconContainer}>
      <Text style={[styles.tabIcon, focused && styles.tabIconFocused]}>
        {icons[name] || "•"}
      </Text>
    </View>
  );
}

// Main Tab Navigator
function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused }) => (
          <TabIcon name={route.name} focused={focused} />
        ),
        tabBarActiveTintColor: "#2563eb",
        tabBarInactiveTintColor: "#6b7280",
        tabBarStyle: styles.tabBar,
        tabBarLabelStyle: styles.tabLabel,
        headerStyle: styles.header,
        headerTitleStyle: styles.headerTitle,
        headerTintColor: "#1f2937",
      })}
    >
      <Tab.Screen
        name="Documents"
        component={DocumentListScreen}
        options={{
          title: "Documents",
          headerTitle: "Lab Reports",
        }}
      />
      <Tab.Screen
        name="Trends"
        component={TrendViewerScreen}
        options={{
          title: "Trends",
          headerTitle: "Health Trends",
        }}
      />
    </Tab.Navigator>
  );
}

// Root Stack Navigator
export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="dark" />
      <Stack.Navigator
        screenOptions={{
          headerStyle: styles.header,
          headerTitleStyle: styles.headerTitle,
          headerTintColor: "#1f2937",
        }}
      >
        <Stack.Screen
          name="DocumentList"
          component={MainTabs}
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="Upload"
          component={UploadScreen}
          options={{
            title: "Upload Report",
            presentation: "modal",
          }}
        />
        <Stack.Screen
          name="DocumentDetail"
          component={DocumentDetailScreen}
          options={{
            title: "Document Details",
          }}
        />
        <Stack.Screen
          name="TrendViewer"
          component={TrendViewerScreen}
          options={{
            title: "Biomarker Trend",
          }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: "#fff",
    borderTopWidth: 1,
    borderTopColor: "#e5e7eb",
    paddingTop: 8,
    paddingBottom: 8,
    height: 60,
  },
  tabLabel: {
    fontSize: 12,
    fontWeight: "600",
  },
  tabIconContainer: {
    alignItems: "center",
    justifyContent: "center",
  },
  tabIcon: {
    fontSize: 24,
    opacity: 0.6,
  },
  tabIconFocused: {
    opacity: 1,
  },
  header: {
    backgroundColor: "#fff",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 3,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#1f2937",
  },
});
