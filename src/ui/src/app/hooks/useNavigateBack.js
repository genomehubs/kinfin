import { useCallback } from "react";
import { useNavigate } from "react-router-dom";

export default function useNavigateBack() {
  const navigate = useNavigate();
  return useCallback(() => {
    try {
      // Prefer router navigation to keep history stack consistent
      navigate(-1);
    } catch (e) {
      // Fallback to window.history when router isn't available
      if (
        typeof window !== "undefined" &&
        window.history &&
        window.history.back
      ) {
        window.history.back();
      }
    }
  }, [navigate]);
}
