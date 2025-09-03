import {
  selectClusteringSets,
  selectSelectedClusterSet,
} from "../app/store/config/selectors/clusteringSelectors";

import React from "react";
import { connect } from "react-redux";
import { getClusteringSets } from "../app/store/config/slices/clusteringSetsSlice";
import { setSelectedClusterSet } from "../app/store/config/slices/uiStateSlice";

export const withClusteringSets = (WrappedComponent) => {
  const mapStateToProps = (state) => {
    const clusteringSets = selectClusteringSets(state);
    const selectedClusterSet = selectSelectedClusterSet(state);
    return {
      clusteringSets,
      selectedClusterSet,
    };
  };

  const mapDispatchToProps = (dispatch) => ({
    setSelectedClusterSet: (clusterSet) =>
      dispatch(setSelectedClusterSet(clusterSet)),
    fetchClusteringSets: () => dispatch(getClusteringSets()),
  });

  return connect(mapStateToProps, mapDispatchToProps)(WrappedComponent);
};

export default withClusteringSets;
