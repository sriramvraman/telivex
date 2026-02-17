# Telivex Mobile App

React Native (Expo) mobile application for the Telivex patient-controlled health reconstruction platform.

## Prerequisites

- Node.js 18+
- Expo CLI
- iOS Simulator (macOS) or Android Emulator

## Setup

```bash
# Install dependencies
npm install

# Start the development server
npx expo start

# Run on iOS simulator
npm run ios

# Run on Android emulator
npm run android

# Run on web
npm run web
```

## Project Structure

```
mobile/
├── App.tsx                 # Root component with navigation
├── src/
│   ├── api/               # API client for backend
│   │   ├── client.ts      # Telivex API client
│   │   └── index.ts
│   ├── components/        # Reusable UI components
│   │   ├── LoadingSpinner.tsx
│   │   ├── ErrorMessage.tsx
│   │   └── index.ts
│   ├── hooks/             # Custom React hooks
│   │   ├── useDocuments.ts
│   │   ├── useTrends.ts
│   │   └── index.ts
│   ├── screens/           # Screen components
│   │   ├── DocumentListScreen.tsx
│   │   ├── UploadScreen.tsx
│   │   ├── DocumentDetailScreen.tsx
│   │   ├── TrendViewerScreen.tsx
│   │   └── index.ts
│   └── types/             # TypeScript type definitions
│       └── index.ts       # API types (mirrors backend schemas)
└── README.md
```

## Features

- **Document Upload**: Capture lab reports via camera or file picker
- **Document List**: View all uploaded documents with extraction stats
- **Event Viewer**: See extracted biomarker events with provenance
- **Trend Charts**: Visualize biomarker trends over time
- **Unmapped Row Review**: Surface rows that couldn't be mapped

## API Configuration

The API client defaults to `http://localhost:8001/api/v1` in development.
For production, update the `API_BASE_URL` in `src/api/client.ts`.

### iOS Simulator
Works with `localhost` directly.

### Android Emulator
Uses `10.0.2.2` to reach the host machine. Update the client if needed.

## Dependencies

- **@react-navigation/native**: Navigation framework
- **@react-navigation/native-stack**: Stack navigator
- **@react-navigation/bottom-tabs**: Tab navigator
- **expo-image-picker**: Camera and photo library access
- **expo-document-picker**: File picker for PDFs
- **react-native-chart-kit**: Chart visualizations
- **react-native-svg**: SVG support for charts

## Type Safety

TypeScript types in `src/types/index.ts` mirror the backend Pydantic schemas.
Keep these in sync when the backend API changes.
