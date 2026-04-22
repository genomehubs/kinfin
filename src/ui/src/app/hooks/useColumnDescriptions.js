import { useGetColumnDescriptionsQuery } from "../store/api";
import { useMemo } from "react";

/**
 * useColumnDescriptions
 * Wrapper around RTK Query `useGetColumnDescriptionsQuery` returning
 * a stable API for components.
 */
export default function useColumnDescriptions({
  page = 1,
  size = 50,
  file,
} = {}) {
  const { data, isLoading, isFetching, error, refetch } =
    useGetColumnDescriptionsQuery({ page, size, file });

  const isBusy = isLoading || isFetching;

  // Normalize server response: some endpoints return an envelope
  // { message, status, data: [...] } while others return the
  // array directly. Ensure consumers always receive an array.

  return useMemo(() => {
    const normalized = Array.isArray(data) ? data : (data?.data ?? []);
    return {
      data: normalized,
      isLoading: isBusy,
      error,
      refetch,
    };
  }, [data, isBusy, error, refetch]);
}
