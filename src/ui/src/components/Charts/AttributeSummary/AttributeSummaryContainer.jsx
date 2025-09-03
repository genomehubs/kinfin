import AttributeSummary from "./AttributeSummary";
import { compose } from "recompose";
import withColumnDescriptions from "../../../hocs/withColumnDescriptions";
import withSelectedAttributeTaxonset from "../../../hocs/withSelectedAttributeTaxonset";

const AttributeSummaryContainer = compose(
  withSelectedAttributeTaxonset,
  withColumnDescriptions
)(AttributeSummary);

export default AttributeSummaryContainer;
