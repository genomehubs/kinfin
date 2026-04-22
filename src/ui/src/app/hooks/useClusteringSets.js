import {
  selectClusteringSets,
  selectSelectedClusterSet,
} from "../store/config/selectors/clusteringSelectors";
import { useDispatch, useSelector } from "react-redux";
import { setSelectedClusterSet } from "../store/config/slices/uiStateSlice";
import { useGetClusteringSetsQuery } from "../store/api";
import { useCallback, useMemo } from "react";

export const useClusteringSets = ({ page = 1, size = 50 } = {}) => {
  const dispatch = useDispatch();
  const { data, isLoading, error, refetch } = useGetClusteringSetsQuery({
    page,
    size,
  });

  // Normalize envelope { data: [...] } -> return array and memoize result
  const normalized = useMemo(
    () => (Array.isArray(data) ? data : (data?.data ?? [])),
    [data],
  );

  // selectors are memoized; useSelector will return stable references where possible
  const clusteringSetsFromSelector = useSelector(selectClusteringSets);
  const selectedClusterSet = useSelector(selectSelectedClusterSet);

  const setSelected = useCallback(
    (clusterSet) => dispatch(setSelectedClusterSet(clusterSet)),
    [dispatch],
  );

  return useMemo(
    () => ({
      data: normalized,
      isLoading,
      error,
      refetch,
      clusteringSets: clusteringSetsFromSelector,
      selectedClusterSet,
      setSelectedClusterSet: setSelected,
    }),
    [
      normalized,
      isLoading,
      error,
      refetch,
      clusteringSetsFromSelector,
      selectedClusterSet,
      setSelected,
    ],
  );
};
