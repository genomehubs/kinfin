import RarefactionCurvePage from "./RarefactionCurvePage";
import React from "react";
import { compose } from "recompose";
import withSelectedAttributeTaxonset from "../../hocs/withSelectedAttributeTaxonset";

const RarefactionCurvePageContainer = compose(withSelectedAttributeTaxonset)(
  RarefactionCurvePage
);

export default RarefactionCurvePageContainer;
