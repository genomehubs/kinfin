import { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useSearchParams } from "react-router-dom";
import { setSelectedAttributeTaxonset } from "../../app/store/config/actions";
import styles from "./AttributeSelector.module.scss";

import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Box,
} from "@mui/material";

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
    setSearchParams(
      {
        attribute,
        taxonset: taxon,
      },
      { replace: true }
    );
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
    setSearchParams(
      {
        attribute: "all",
        taxonset: "all",
      },
      { replace: true }
    );
    dispatch(
      setSelectedAttributeTaxonset({
        attribute: "all",
        taxonset: "all",
      })
    );
  };

  return (
    <Box className={styles.container}>
      <Box className={styles.selectors}>
        <FormControl fullWidth size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Attribute</InputLabel>
          <Select
            value={attribute}
            onChange={handleAttributeChange}
            label="Attribute"
          >
            <MenuItem value="">Select Attribute</MenuItem>
            {responseData?.attributes?.map((attr) => (
              <MenuItem key={attr} value={attr}>
                {attr}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl
          fullWidth
          size="small"
          sx={{ minWidth: 200 }}
          disabled={!attribute}
        >
          <InputLabel>Taxon Set</InputLabel>
          <Select value={taxon} onChange={handleTaxonChange} label="Taxon Set">
            <MenuItem value="">Select Taxon Set</MenuItem>
            {attribute &&
              responseData?.taxon_set[attribute]?.map((tx) => (
                <MenuItem key={tx} value={tx}>
                  {tx}
                </MenuItem>
              ))}
          </Select>
        </FormControl>
      </Box>

      <Box className={styles.buttonContainer} sx={{ display: "flex", gap: 1 }}>
        <Button
          sx={{
            textTransform: "none",
          }}
          variant="contained"
          color="primary"
          onClick={handleApply}
        >
          Apply
        </Button>
        <Button
          sx={{
            textTransform: "none",
          }}
          variant="outlined"
          color="primary"
          onClick={handleClear}
        >
          Clear
        </Button>
      </Box>
    </Box>
  );
};

export default AttributeSelector;
