const selectClusteringSets = (state) =>
  state?.config?.clusteringSets.data || [];
const selectSelectedClusterSet = (state) =>
  state?.config?.uiState?.selectedClusterSet;

export { selectClusteringSets, selectSelectedClusterSet };
