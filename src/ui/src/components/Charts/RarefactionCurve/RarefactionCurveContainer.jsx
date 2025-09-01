import RarefactionCurve from "./RarefactionCurve";
import { compose } from "recompose";
import withRarefactionCurve from "../../../hocs/withRarefactionCurve";
import withSelectedAttributeTaxonset from "../../../hocs/withSelectedAttributeTaxonset";

const RarefactionCurveContainer = compose(
  withSelectedAttributeTaxonset,
  withRarefactionCurve
)(RarefactionCurve);

export default RarefactionCurveContainer;
