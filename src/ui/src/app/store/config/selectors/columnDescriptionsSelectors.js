import { createSelector } from "reselect";

const selectColumnDescriptions = (state) =>
  state?.config?.columnDescriptions || { data: [] };

const selectAttributeSummaryColumnDescriptions = createSelector(
  selectColumnDescriptions,
  (columnDescriptions) =>
    columnDescriptions.data.filter(
      (col) => col.file === "*.attribute_metrics.txt"
    )
);

const selectClusterSummaryColumnDescriptions = createSelector(
  selectColumnDescriptions,
  (columnDescriptions) =>
    columnDescriptions.data.filter(
      (col) => col.file === "*.cluster_summary.txt"
    )
);

const selectClusterMetricsColumnDescriptions = createSelector(
  selectColumnDescriptions,
  (columnDescriptions) =>
    columnDescriptions.data.filter(
      (col) => col.file === "*.cluster_metrics.txt"
    )
);

export {
  selectColumnDescriptions,
  selectAttributeSummaryColumnDescriptions,
  selectClusterSummaryColumnDescriptions,
  selectClusterMetricsColumnDescriptions,
};
