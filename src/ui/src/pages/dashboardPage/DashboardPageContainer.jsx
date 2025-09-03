import DashboardPage from "./DashboardPage";
import React from "react";
import { compose } from "recompose";
import withClusterSizeDistribution from "../../hocs/withClusterSizeDistribution";
import withRarefactionCurve from "../../hocs/withRarefactionCurve";
import withSelectedAttributeTaxonset from "../../hocs/withSelectedAttributeTaxonset";

const DashboardPageContainer = compose(
  withSelectedAttributeTaxonset,
  withClusterSizeDistribution,
  withRarefactionCurve
)(DashboardPage);

export default DashboardPageContainer;
