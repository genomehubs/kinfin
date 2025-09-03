import ClusterSummaryPage from "./ClusterSummaryPage";
import React from "react";
import { compose } from "recompose";
import withColumnDescriptions from "../../hocs/withColumnDescriptions";
import withSelectedAttributeTaxonset from "../../hocs/withSelectedAttributeTaxonset";

const ClusterSummaryPageContainer = compose(
  withSelectedAttributeTaxonset,
  withColumnDescriptions
)(ClusterSummaryPage);

export default ClusterSummaryPageContainer;
