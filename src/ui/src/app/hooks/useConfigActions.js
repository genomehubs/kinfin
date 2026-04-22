import { deleteConfig as deleteConfigAction } from "../store/config/slices/configSlice";
import { useCallback } from "react";
import { useDispatch } from "react-redux";

/**
 * useConfigActions
 * Thin hook wrapper around `deleteConfig` slice action.
 * Keeps the same semantics but provides a hooks-based API for components.
 */
export default function useConfigActions() {
  const dispatch = useDispatch();

  const deleteConfig = useCallback(
    (sessionId) => dispatch(deleteConfigAction(sessionId)),
    [dispatch],
  );

  return { deleteConfig };
}
