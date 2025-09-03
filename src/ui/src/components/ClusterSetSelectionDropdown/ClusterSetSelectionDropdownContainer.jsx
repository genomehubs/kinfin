import ClusterSetSelectionDropdown from "./ClusterSetSelectionDropdown";
import { compose } from "recompose";
import withClusteringSets from "../../hocs/withClusteringSets";

const ClusterSetSelectionDropdownContainer = compose(withClusteringSets)(
  ClusterSetSelectionDropdown
);

export default ClusterSetSelectionDropdownContainer;
