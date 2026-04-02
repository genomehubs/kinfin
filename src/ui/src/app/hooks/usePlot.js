import { useMemo } from "react";
import { useGetPlotQuery } from "#store/api";

const usePlot = ({ attribute, plotType }, options = {}) => {
  const query = useGetPlotQuery({ attribute, plotType }, options);

  const normalized = useMemo(() => {
    const raw = query.data;
    if (raw == null) return null;
    const isBlob = typeof Blob !== "undefined" && raw instanceof Blob;
    if (isBlob) {
      return { data: raw, filename: null, format: "blob", raw };
    }
    if (typeof raw === "object") {
      return { data: raw, filename: null, format: "json", raw };
    }
    return { data: raw, filename: null, format: "text", raw };
  }, [query.data]);

  return { ...query, data: normalized };
};

export default usePlot;
