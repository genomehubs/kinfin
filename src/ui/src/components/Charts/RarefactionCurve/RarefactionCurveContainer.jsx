import RarefactionCurve from "./RarefactionCurve";
import { compose } from "recompose";
import withSelectedAttributeTaxonset from "../../../hocs/withSelectedAttributeTaxonset";

const RarefactionCurveContainer = compose(withSelectedAttributeTaxonset)(
  RarefactionCurve
);

export default RarefactionCurveContainer;
