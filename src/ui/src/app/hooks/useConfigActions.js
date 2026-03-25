import {
  deleteConfig as deleteConfigAction,
  renameConfig as renameConfigAction,
} from "../store/config/slices/configSlice";

import { useCallback } from "react";
import { useDispatch } from "react-redux";

/**
 * useConfigActions
 * Thin hook wrapper around `renameConfig` and `deleteConfig` slice actions.
 * Keeps the same semantics but provides a hooks-based API for components.
 */
export default function useConfigActions() {
  const dispatch = useDispatch();

  const renameConfig = useCallback(
    (payload) => dispatch(renameConfigAction(payload)),
    [dispatch],
  );

  const deleteConfig = useCallback(
    (sessionId) => dispatch(deleteConfigAction(sessionId)),
    [dispatch],
  );

  return { renameConfig, deleteConfig };
}
