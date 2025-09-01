import ClusterMetrics from "./ClusterMetrics";
import { compose } from "recompose";
import withSelectedAttributeTaxonset from "../../../hocs/withSelectedAttributeTaxonset";

const ClusterMetricsContainer = compose(withSelectedAttributeTaxonset)(
  ClusterMetrics
);

export default ClusterMetricsContainer;
