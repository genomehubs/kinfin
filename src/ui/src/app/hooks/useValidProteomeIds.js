import { useGetValidProteomeIdsQuery } from "#store/api.js";

// Forward params (or skipToken) to the RTK Query hook so callers can
// opt-out (skipToken) or pass { clusterId, page, size }.
export const useValidProteomeIds = (params) => {
  const { data, isLoading, error } = useGetValidProteomeIdsQuery(params);

  const normalized = data?.data ?? data ?? {};

  return { data: normalized, isLoading, error };
};
