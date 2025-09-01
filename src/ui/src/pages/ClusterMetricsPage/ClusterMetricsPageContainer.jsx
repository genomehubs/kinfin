import ClusterMetricsPage from "./ClusterMetricsPage";
import React from "react";
import { compose } from "recompose";
import withSelectedAttributeTaxonset from "../../hocs/withSelectedAttributeTaxonset";

const ClusterMetricsPageContainer = compose(withSelectedAttributeTaxonset)(
  ClusterMetricsPage
);

export default ClusterMetricsPageContainer;
