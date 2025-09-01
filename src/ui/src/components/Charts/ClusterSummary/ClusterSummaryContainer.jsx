import ClusterSummary from "./ClusterSummary";
import { compose } from "recompose";
import withSelectedAttributeTaxonset from "../../../hocs/withSelectedAttributeTaxonset";

const ClusterSummaryContainer = compose(withSelectedAttributeTaxonset)(
  ClusterSummary
);

export default ClusterSummaryContainer;
