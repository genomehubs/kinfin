import { createSelector } from "reselect";

const getPlotData = (state) => state?.analysis?.plot?.data;

export const getRarefactionCurve = createSelector(
  [getPlotData],
  (data) => data?.rarefactionCurve
);

export const getClusterSizeDistribution = createSelector(
  [getPlotData],
  (data) => data?.clusterSizeDistribution
);
