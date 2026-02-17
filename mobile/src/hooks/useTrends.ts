/**
 * Hook for trend data operations.
 */

import { useState, useCallback } from "react";
import { apiClient } from "../api/client";
import type { BiomarkerTrend, LabEventResponse } from "../types";

export function useTrends() {
  const [trends, setTrends] = useState<BiomarkerTrend[]>([]);
  const [selectedTrend, setSelectedTrend] = useState<BiomarkerTrend | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAllTrends = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getAllTrends();
      setTrends(data);
    } catch (err) {
      // Trends endpoint might not be implemented yet
      // Fall back to constructing trends from events
      setError(err instanceof Error ? err.message : "Failed to fetch trends");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchBiomarkerTrend = useCallback(async (biomarkerId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getBiomarkerTrend(biomarkerId);
      setSelectedTrend(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch trend");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Helper to construct trend data from events (fallback if trend endpoint not available)
  const constructTrendFromEvents = useCallback(
    (events: LabEventResponse[], analyteName: string): BiomarkerTrend | null => {
      if (events.length === 0) return null;

      const firstEvent = events[0];
      return {
        biomarker_id: firstEvent.biomarker_id,
        analyte_name: analyteName,
        unit: firstEvent.unit_canonical,
        data_points: events.map((e) => ({
          event_id: e.event_id,
          collected_at: e.collected_at,
          value: e.value_normalized,
          unit: e.unit_canonical,
        })),
      };
    },
    []
  );

  return {
    trends,
    selectedTrend,
    loading,
    error,
    fetchAllTrends,
    fetchBiomarkerTrend,
    constructTrendFromEvents,
  };
}
