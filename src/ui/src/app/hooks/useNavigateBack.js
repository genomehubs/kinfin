import { useCallback } from "react";
import { useNavigate } from "react-router-dom";

export default function useNavigateBack() {
  const navigate = useNavigate();

  return useCallback(() => {
    try {
      // If we're on a chart/table route (e.g. /:sessionId/cluster-summary/...)
      // take the user straight back to the dashboard pack root for that
      // session instead of stepping through intermediate history states.
      const pathname =
        typeof window !== "undefined" ? window.location.pathname : "";
      const m = pathname.match(
        /^\/([^/]+)\/(cluster-summary|attribute-summary|cluster-metrics|rarefaction-curve|cluster-size-distribution)/,
      );
      if (m) {
        const sessionId = m[1];
        navigate(`/${sessionId}/`, { replace: true });
        return;
      }

      // Default: step back one entry in history
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
  }, [navigate, location]);
}
