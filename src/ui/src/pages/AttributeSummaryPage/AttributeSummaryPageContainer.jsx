import AttributeSummaryPage from "./AttributeSummaryPage";
import React from "react";
import { compose } from "recompose";
import withSelectedAttributeTaxonset from "../../hocs/withSelectedAttributeTaxonset";

const AttributeSummaryPageContainer = compose(withSelectedAttributeTaxonset)(
  AttributeSummaryPage
);

export default AttributeSummaryPageContainer;
