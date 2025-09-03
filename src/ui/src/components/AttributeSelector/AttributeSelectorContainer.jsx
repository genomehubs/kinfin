import AttributeSelector from "./AttributeSelector";
import { compose } from "recompose";
import withSelectedAttributeTaxonset from "../../hocs/withSelectedAttributeTaxonset";

const AttributeSelectorContainer = compose(withSelectedAttributeTaxonset)(
  AttributeSelector
);

export default AttributeSelectorContainer;
