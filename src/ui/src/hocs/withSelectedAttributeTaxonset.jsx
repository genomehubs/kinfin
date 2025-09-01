import React from "react";
import { connect } from "react-redux";
import { getSelectedAttributeTaxonset } from "../app/store/config/selectors/uiStateSelectors";
import { setSelectedAttributeTaxonset } from "../app/store/config/slices/uiStateSlice";

export const withSelectedAttributeTaxonset = (WrappedComponent) => {
  const mapStateToProps = (state) => {
    const selectedAttributeTaxonset = getSelectedAttributeTaxonset(state);
    return {
      selectedAttributeTaxonset,
      attribute: selectedAttributeTaxonset.attribute,
      taxonset: selectedAttributeTaxonset.taxonset,
    };
  };

  const mapDispatchToProps = (dispatch) => ({
    setSelectedAttributeTaxonset: (payload) => {
      dispatch(setSelectedAttributeTaxonset(payload));
    },
  });

  return connect(mapStateToProps, mapDispatchToProps)(WrappedComponent);
};

export default withSelectedAttributeTaxonset;
