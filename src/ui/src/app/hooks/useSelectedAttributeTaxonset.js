import { useDispatch, useSelector } from "react-redux";

import { getSelectedAttributeTaxonset } from "../store/config/selectors/uiStateSelectors";
import { setSelectedAttributeTaxonset } from "../store/config/slices/uiStateSlice";

const useSelectedAttributeTaxonset = () => {
  const dispatch = useDispatch();
  const selected = useSelector((state) => getSelectedAttributeTaxonset(state));

  const setSelected = (payload) =>
    dispatch(setSelectedAttributeTaxonset(payload));

  return {
    selectedAttributeTaxonset: selected,
    attribute: selected.attribute,
    taxonset: selected.taxonset,
    setSelectedAttributeTaxonset: setSelected,
  };
};

export default useSelectedAttributeTaxonset;
