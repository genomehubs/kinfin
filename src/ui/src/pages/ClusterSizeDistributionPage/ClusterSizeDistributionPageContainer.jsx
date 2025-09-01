import ClusterSizeDistributionPage from "./ClusterSizeDistributionPage";
import React from "react";
import { compose } from "recompose";
import withClusterSizeDistribution from "../../hocs/withClusterSizeDistribution";
import withSelectedAttributeTaxonset from "../../hocs/withSelectedAttributeTaxonset";

const ClusterSizeDistributionPageContainer = compose(
  withSelectedAttributeTaxonset,
  withClusterSizeDistribution
)(ClusterSizeDistributionPage);

export default ClusterSizeDistributionPageContainer;
