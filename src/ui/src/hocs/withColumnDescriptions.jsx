import {
  selectAttributeSummaryColumnDescriptions,
  selectClusterMetricsColumnDescriptions,
  selectClusterSummaryColumnDescriptions,
} from "../app/store/config/selectors/columnDescriptionsSelectors";

import React from "react";
import { connect } from "react-redux";

export const withColumnDescriptions = (WrappedComponent) => {
  const mapStateToProps = (state) => {
    return {
      attributeSummaryColumnDescriptions:
        selectAttributeSummaryColumnDescriptions(state) || [],
      clusterSummaryColumnDescriptions:
        selectClusterSummaryColumnDescriptions(state) || [],
      clusterMetricsColumnDescriptions:
        selectClusterMetricsColumnDescriptions(state) || [],
    };
  };

  return connect(mapStateToProps)(WrappedComponent);
};

export default withColumnDescriptions;
