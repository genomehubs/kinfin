import DefineNodeLabelsPage from "./DefineNodeLabelsPage";
import React from "react";
import { compose } from "recompose";
import withClusterSizeDistribution from "../../hocs/withClusterSizeDistribution";
import withClusteringSets from "../../hocs/withClusteringSets";
import withRarefactionCurve from "../../hocs/withRarefactionCurve";
import withSelectedAttributeTaxonset from "../../hocs/withSelectedAttributeTaxonset";

const DefineNodeLabelsPageContainer = compose(
  withSelectedAttributeTaxonset,
  withClusterSizeDistribution,
  withRarefactionCurve,
  withClusteringSets
)(DefineNodeLabelsPage);

export default DefineNodeLabelsPageContainer;
