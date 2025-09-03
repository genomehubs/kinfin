import { createSelector } from "reselect";

const getSelectedAttributeTaxonset = createSelector(
  (state) => state?.config?.uiState?.selectedAttributeTaxonset,
  (selected) => {
    let { attribute = "all", taxonset = "all" } = selected || {};
    return {
      attribute,
      taxonset,
    };
  }
);

export { getSelectedAttributeTaxonset };
