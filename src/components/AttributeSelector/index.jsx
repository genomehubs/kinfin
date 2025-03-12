import { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import * as AnalysisActions from "../../app/store/kinfin/actions";
import styles from "./attributeSelector.module.scss";
const AttributeSelector = () => {
  const dispatch = useDispatch();

  const responseData = useSelector(
    (state) => state?.analysis?.availableAttributesTaxonsets?.data
  );

  // Get persisted values from Redux
  const persistedSelection = useSelector(
    (state) => state?.analysis?.selectedAttributeTaxonset
  );
  console.log(
    "🚀 ~ AttributeSelector ~ persistedSelection:",
    persistedSelection
  );

  // Initialize state with persisted values
  const [selectedAttribute, setSelectedAttribute] = useState("");
  const [selectedTaxon, setSelectedTaxon] = useState("");

  useEffect(() => {
    if (persistedSelection) {
      setSelectedAttribute(persistedSelection.attribute || "");
      setSelectedTaxon(persistedSelection.taxonset || "");
    }
  }, [persistedSelection]); // Run when persistedSelection changes

  const handleAttributeChange = (e) => {
    const attribute = e.target.value;
    setSelectedAttribute(attribute);
    setSelectedTaxon(""); // Reset taxon selection when attribute changes
  };

  const handleTaxonChange = (e) => {
    setSelectedTaxon(e.target.value);
  };

  const handleApply = () => {
    if (selectedAttribute && selectedTaxon) {
      console.log("hi");
      dispatch(
        AnalysisActions.setSelectedAttributeTaxonset({
          attribute: selectedAttribute,
          taxonset: selectedTaxon,
        })
      );
    }
  };

  const handleClear = () => {
    setSelectedAttribute("");
    setSelectedTaxon("");
    dispatch(
      AnalysisActions.setSelectedAttributeTaxonset({
        attribute: null,
        taxonset: null,
      })
    ); // Clear Redux state
  };

  return (
    <div className={styles.container}>
      <div className={styles.selectors}>
        <div className={styles.selectContainer}>
          <label>Attribute: </label>
          <select
            className={styles.dropdown}
            onChange={handleAttributeChange}
            value={selectedAttribute}
          >
            <option value="">Select Attribute</option>
            {responseData?.attributes?.map((attr) => (
              <option key={attr} value={attr}>
                {attr}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.selectContainer}>
          <label> Taxon Set: </label>
          <select
            className={styles.dropdown}
            onChange={handleTaxonChange}
            value={selectedTaxon}
            disabled={!selectedAttribute}
          >
            <option value="">Select Taxon Set</option>
            {selectedAttribute &&
              responseData?.taxon_set[selectedAttribute]?.map((taxon) => (
                <option key={taxon} value={taxon}>
                  {taxon}
                </option>
              ))}
          </select>
        </div>
      </div>

      <div className={styles.buttonContainer}>
        <button
          className={styles.applyButton}
          onClick={handleApply}
          disabled={!selectedAttribute || !selectedTaxon}
        >
          Apply
        </button>
        <button className={styles.clearButton} onClick={handleClear}>
          Clear
        </button>
      </div>
    </div>
  );
};

export default AttributeSelector;
