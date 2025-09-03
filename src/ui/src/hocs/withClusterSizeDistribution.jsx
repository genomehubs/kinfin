import React from "react";
import { connect } from "react-redux";
import { getClusterSizeDistribution } from "../app/store/analysis/selectors/plotSelectors";

export const withClusterSizeDistribution = (WrappedComponent) => {
  const mapStateToProps = (state) => {
    const clusterSizeDistributionBlob = getClusterSizeDistribution(state);
    return {
      clusterSizeDistributionBlob,
    };
  };

  return connect(mapStateToProps)(WrappedComponent);
};

export default withClusterSizeDistribution;
