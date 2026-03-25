import { useMemo } from "react";
import { useLocation } from "react-router-dom";

export default function useIsCurrentPage(fragment) {
  const location = useLocation();
  return useMemo(() => {
    if (!fragment) return false;
    const path = location?.pathname || "";
    return path.includes(fragment);
  }, [location, fragment]);
}
