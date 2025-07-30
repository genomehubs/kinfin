import { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useSearchParams } from "react-router-dom";
import { setSelectedAttributeTaxonset } from "../../app/store/config/actions";
import styles from "./AttributeSelector.module.scss";

const AttributeSelector = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const responseData = useSelector(
    (state) => state?.analysis?.availableAttributesTaxonsets?.data
  );

  // Read from URL initially
  const initialAttribute = searchParams.get("attribute") || "";
  const initialTaxon = searchParams.get("taxonset") || "";

  const [attribute, setAttribute] = useState(initialAttribute);
  const [taxon, setTaxon] = useState(initialTaxon);

  // Apply selection when URL params change
  useEffect(() => {
    if (initialAttribute && initialTaxon) {
      dispatch(
        setSelectedAttributeTaxonset({
          attribute: initialAttribute,
          taxonset: initialTaxon,
        })
      );
    }
  }, [initialAttribute, initialTaxon, dispatch]);

  const handleAttributeChange = (e) => {
    const newAttribute = e.target.value;
    setAttribute(newAttribute);
    setTaxon(""); // Reset taxonset when attribute changes
  };

  const handleTaxonChange = (e) => {
    setTaxon(e.target.value);
  };

  const handleApply = () => {
    setSearchParams({
      attribute,
      taxonset: taxon,
    });
    dispatch(
      setSelectedAttributeTaxonset({
        attribute,
        taxonset: taxon,
      })
    );
  };

  const handleClear = () => {
    setAttribute("all");
    setTaxon("all");
    setSearchParams({
      attribute: "all",
      taxonset: "all",
    });
    dispatch(
      setSelectedAttributeTaxonset({
        attribute: "all",
        taxonset: "all",
      })
    );
  };

  return (
    <div className={styles.container}>
      <div className={styles.selectors}>
        <div className={styles.selectContainer}>
          <label>Attribute:</label>
          <select
            className={styles.dropdown}
            onChange={handleAttributeChange}
            value={attribute}
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
          <label>Taxon Set:</label>
          <select
            className={styles.dropdown}
            onChange={handleTaxonChange}
            value={taxon}
            disabled={!attribute}
          >
            <option value="">Select Taxon Set</option>
            {attribute &&
              responseData?.taxon_set[attribute]?.map((tx) => (
                <option key={tx} value={tx}>
                  {tx}
                </option>
              ))}
          </select>
        </div>
      </div>

      <div className={styles.buttonContainer}>
        <button className={styles.applyButton} onClick={handleApply}>
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
