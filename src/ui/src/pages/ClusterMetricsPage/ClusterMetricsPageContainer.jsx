import ClusterMetricsPage from "./ClusterMetricsPage";
import React from "react";
import { compose } from "recompose";
import withColumnDescriptions from "../../hocs/withColumnDescriptions";
import withSelectedAttributeTaxonset from "../../hocs/withSelectedAttributeTaxonset";

const ClusterMetricsPageContainer = compose(
  withSelectedAttributeTaxonset,
  withColumnDescriptions
)(ClusterMetricsPage);

export default ClusterMetricsPageContainer;
