import { createSelector } from "@reduxjs/toolkit";

const selectConfig = (state) => state?.config || {};

const selectClusteringSets = createSelector(
  selectConfig,
  (config) => config?.clusteringSets?.data ?? [],
);

const selectSelectedClusterSet = (state) =>
  state?.config?.uiState?.selectedClusterSet;

export { selectClusteringSets, selectSelectedClusterSet };
