import ClusterSizeDistribution from "./ClusterSizeDistribution";
import { compose } from "recompose";
import withClusterSizeDistribution from "../../../hocs/withClusterSizeDistribution";
import withSelectedAttributeTaxonset from "../../../hocs/withSelectedAttributeTaxonset";

const ClusterSizeDistributionContainer = compose(
  withSelectedAttributeTaxonset,
  withClusterSizeDistribution
)(ClusterSizeDistribution);

export default ClusterSizeDistributionContainer;
