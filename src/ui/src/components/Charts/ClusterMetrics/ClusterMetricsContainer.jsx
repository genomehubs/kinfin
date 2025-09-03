import ClusterMetrics from "./ClusterMetrics";
import { compose } from "recompose";
import withColumnDescriptions from "../../../hocs/withColumnDescriptions";
import withSelectedAttributeTaxonset from "../../../hocs/withSelectedAttributeTaxonset";

const ClusterMetricsContainer = compose(
  withSelectedAttributeTaxonset,
  withColumnDescriptions
)(ClusterMetrics);

export default ClusterMetricsContainer;
