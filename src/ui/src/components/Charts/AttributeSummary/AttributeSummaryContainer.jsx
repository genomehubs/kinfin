import AttributeSummary from "./AttributeSummary";
import { compose } from "recompose";
import withSelectedAttributeTaxonset from "../../../hocs/withSelectedAttributeTaxonset";

const AttributeSummaryContainer = compose(withSelectedAttributeTaxonset)(
  AttributeSummary
);

export default AttributeSummaryContainer;
