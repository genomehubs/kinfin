import { useCallback, useEffect, useState } from "react";

import useColumnSettings from "#hooks/useColumnSettings";
import { useSearchParams } from "react-router-dom";

// Hook to manage selected codes synced with URL search params and a customise dialog
export default function usePageCustomisation({
  searchParamKey,
  columnDescriptions = [],
} = {}) {
  const [searchParams] = useSearchParams();
  const [customiseOpen, setCustomiseOpen] = useState(false);

  const columnSettingsHook = useColumnSettings(
    /* tableKey */ searchParamKey || "",
    { searchParamKey },
  );

  // Ensure settings are restored from localStorage into the hook/store on mount
  // Do not auto-restore from localStorage on mount. The URL must be the
  // source of truth on page load/reload. localStorage is only written to
  // when settings change; Redux holds the in-memory state during SPA
  // navigation so selections persist across internal navigation.

  // Derive selected codes from store/hook. If `columnDescriptions` are not yet
  // available (e.g. on Dashboard while metadata loads) prefer the store value
  // directly so URL-provided selections are respected. Only sanitize against
  // `columnDescriptions` when those descriptions are present.
  const selectedCodes = (() => {
    const defaults = (columnDescriptions || [])
      .filter((col) => col.isDefault)
      .map((c) => c.code);
    const fromStore = columnSettingsHook?.settings;
    if (!fromStore || !Array.isArray(fromStore) || fromStore.length === 0)
      return defaults;
    // If we don't have columnDescriptions yet, return stored settings as-is
    if (!columnDescriptions || columnDescriptions.length === 0)
      return fromStore;
    const validCodes = (columnDescriptions || []).map((c) => c.code);
    const sanitized = fromStore.filter((c) => validCodes.includes(c));
    return sanitized.length > 0 ? sanitized : defaults;
  })();

  const openCustomise = useCallback(() => setCustomiseOpen(true), []);

  const handleApply = useCallback(
    (newSelectedCodes) => {
      if (columnSettingsHook && columnSettingsHook.setSettings) {
        columnSettingsHook.setSettings(newSelectedCodes);
      }
      setCustomiseOpen(false);
    },
    [columnSettingsHook],
  );

  const handleCancel = useCallback(() => setCustomiseOpen(false), []);

  return {
    selectedCodes,
    setSelectedCodes: columnSettingsHook?.setSettings || (() => {}),
    customiseOpen,
    openCustomise,
    handleApply,
    handleCancel,
  };
}
