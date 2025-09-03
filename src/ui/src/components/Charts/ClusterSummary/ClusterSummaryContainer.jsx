import ClusterSummary from "./ClusterSummary";
import { compose } from "recompose";
import withColumnDescriptions from "../../../hocs/withColumnDescriptions";
import withSelectedAttributeTaxonset from "../../../hocs/withSelectedAttributeTaxonset";

const ClusterSummaryContainer = compose(
  withSelectedAttributeTaxonset,
  withColumnDescriptions
)(ClusterSummary);

export default ClusterSummaryContainer;
