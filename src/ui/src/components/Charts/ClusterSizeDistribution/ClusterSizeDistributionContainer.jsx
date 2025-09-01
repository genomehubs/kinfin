import ClusterSizeDistribution from "./ClusterSizeDistribution";
import { compose } from "recompose";
import withSelectedAttributeTaxonset from "../../../hocs/withSelectedAttributeTaxonset";

const ClusterSizeDistributionContainer = compose(withSelectedAttributeTaxonset)(
  ClusterSizeDistribution
);

export default ClusterSizeDistributionContainer;
