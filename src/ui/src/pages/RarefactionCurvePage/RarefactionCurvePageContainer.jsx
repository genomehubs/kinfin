import RarefactionCurvePage from "./RarefactionCurvePage";
import React from "react";
import { compose } from "recompose";
import withRarefactionCurve from "../../hocs/withRarefactionCurve";
import withSelectedAttributeTaxonset from "../../hocs/withSelectedAttributeTaxonset";

const RarefactionCurvePageContainer = compose(
  withSelectedAttributeTaxonset,
  withRarefactionCurve
)(RarefactionCurvePage);

export default RarefactionCurvePageContainer;
