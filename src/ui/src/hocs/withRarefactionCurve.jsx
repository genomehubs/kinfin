import React from "react";
import { connect } from "react-redux";
import { getRarefactionCurve } from "../app/store/analysis/selectors/plotSelectors";

export const withRarefactionCurve = (WrappedComponent) => {
  const mapStateToProps = (state) => {
    const rarefactionCurveBlob = getRarefactionCurve(state);
    return {
      rarefactionCurveBlob,
    };
  };

  return connect(mapStateToProps)(WrappedComponent);
};

export default withRarefactionCurve;
