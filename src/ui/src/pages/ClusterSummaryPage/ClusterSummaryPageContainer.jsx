import ClusterSummaryPage from "./ClusterSummaryPage";
import React from "react";
import { compose } from "recompose";
import withSelectedAttributeTaxonset from "../../hocs/withSelectedAttributeTaxonset";

const ClusterSummaryPageContainer = compose(withSelectedAttributeTaxonset)(
  ClusterSummaryPage
);

export default ClusterSummaryPageContainer;
