import { setSelectedClusterSet as setSelectedClusterSetAction } from "../store/config/slices/uiStateSlice";
import { useCallback } from "react";
import { useDispatch } from "react-redux";

export default function useUIStateActions() {
  const dispatch = useDispatch();
  const setSelectedClusterSet = useCallback(
    (value) => dispatch(setSelectedClusterSetAction(value)),
    [dispatch],
  );
  return { setSelectedClusterSet };
}
