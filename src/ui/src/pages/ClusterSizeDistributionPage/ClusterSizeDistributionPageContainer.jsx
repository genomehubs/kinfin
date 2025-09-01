import ClusterSizeDistributionPage from "./ClusterSizeDistributionPage";
import React from "react";
import { compose } from "recompose";
import withSelectedAttributeTaxonset from "../../hocs/withSelectedAttributeTaxonset";

const ClusterSizeDistributionPageContainer = compose(
  withSelectedAttributeTaxonset
)(ClusterSizeDistributionPage);

export default ClusterSizeDistributionPageContainer;
