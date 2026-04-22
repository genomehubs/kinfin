import {
  mergeRepeatedParams,
  parseConcatCodes,
  serializeCodes,
} from "../utils/columnCodes";
import { useCallback, useEffect, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";

import { setColumnSettings } from "../store/config/slices/uiStateSlice";
import { useSearchParams } from "react-router-dom";

const LS_PREFIX = "kinfin.columnSettings.";

// Do not persist column selections to localStorage by default (MVP)
// to keep URL and in-memory Redux as sources of truth.

export default function useColumnSettings(tableKey, { searchParamKey } = {}) {
  const dispatch = useDispatch();
  const storeSettings = useSelector(
    (s) => s?.config?.uiState?.columnSettings?.[tableKey],
  );
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize from URL > Redux > localStorage > empty
  const initialFromUrl = useMemo(() => {
    if (!searchParamKey) return null;
    if (!searchParams.has(searchParamKey)) return null;
    const all = searchParams.getAll(searchParamKey);
    const canonical = all.length > 1 ? mergeRepeatedParams(all) : all[0] || "";
    return parseConcatCodes(canonical);
  }, [searchParams, searchParamKey]);
  // Do not restore from localStorage on mount. The URL is the source of truth
  // on page load/reload; localStorage is only used as persistence on setting
  // and for diagnostics, but we rely on in-memory Redux state during SPA
  // navigation to preserve selections.
  const initial = initialFromUrl ?? storeSettings ?? null;

  // ensure store has initial only when we have a real initial source (url or local),
  // or when storeSettings already exists but differs from initial.
  useEffect(() => {
    const shouldSetFromUrl = initialFromUrl != null;
    if (
      shouldSetFromUrl ||
      (storeSettings &&
        JSON.stringify(storeSettings) !== JSON.stringify(initial))
    ) {
      dispatch(setColumnSettings({ tableKey, settings: initial ?? [] }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialFromUrl, storeSettings, tableKey]);

  // If this is a full page load/reload and the URL does NOT contain the
  // `searchParamKey`, then the URL is explicitly saying "no custom columns".
  // In that case reset stored settings to an empty array so components fall
  // back to their default columns. Do NOT do this for SPA internal
  // navigation where we want to preserve in-memory selections.
  useEffect(() => {
    try {
      if (!searchParamKey) return;
      // detect navigation type using PerformanceNavigationTiming when available
      const navEntries =
        performance && performance.getEntriesByType
          ? performance.getEntriesByType("navigation")
          : [];
      const navType = navEntries && navEntries[0] && navEntries[0].type;
      const isFullPageLoad =
        navType === "reload" ||
        navType === "navigate" ||
        (performance &&
          performance.navigation &&
          performance.navigation.type === 1);

      if (isFullPageLoad && !searchParams.has(searchParamKey)) {
        // Explicitly clear stored settings so URL (which has no param)
        // becomes the source of truth and components show defaults.
        dispatch(setColumnSettings({ tableKey, settings: [] }));
      }
    } catch (e) {
      // ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setSettings = useCallback(
    (settings) => {
      // update redux
      dispatch(setColumnSettings({ tableKey, settings }));
      // update URL if searchParamKey provided
      if (searchParamKey) {
        const serialized = serializeCodes(settings || []);
        setSearchParams(
          (prev) => {
            const newParams = new URLSearchParams(prev);
            newParams.delete(searchParamKey);
            if (serialized) newParams.append(searchParamKey, serialized);
            return newParams;
          },
          { replace: true },
        );
      }
    },
    [dispatch, tableKey, searchParamKey, setSearchParams],
  );

  const createPermalink = useCallback(() => {
    if (!searchParamKey) return;
    const serialized = serializeCodes(storeSettings || initial || []);
    setSearchParams(
      (prev) => {
        const newParams = new URLSearchParams(prev);
        newParams.delete(searchParamKey);
        if (serialized) newParams.append(searchParamKey, serialized);
        return newParams;
      },
      { replace: false },
    );
  }, [searchParamKey, setSearchParams, storeSettings, initial]);

  return {
    settings: storeSettings ?? initial,
    setSettings,
    createPermalink,
  };
}
