import { useGetColumnDescriptionsQuery } from "../store/api";
import { useMemo } from "react";

export default function useColumnDescriptionsSets() {
  const { data, isLoading, isFetching, error, refetch } =
    useGetColumnDescriptionsQuery();

  // Normalize response to always be an array. Server sometimes returns
  // an envelope like { message, status, data: [...] }.
  const list = useMemo(
    () => (Array.isArray(data) ? data : (data?.data ?? [])),
    [data],
  );

  const attributeSummary = useMemo(
    () => list.filter((col) => col.file === "*.attribute_metrics.txt"),
    [list],
  );

  const clusterSummary = useMemo(
    () => list.filter((col) => col.file === "*.cluster_summary.txt"),
    [list],
  );

  const clusterMetrics = useMemo(
    () => list.filter((col) => col.file === "*.cluster_metrics.txt"),
    [list],
  );

  return {
    attributeSummary,
    clusterSummary,
    clusterMetrics,
    isLoading: isLoading || isFetching,
    error,
    refetch,
  };
}
