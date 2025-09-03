import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
} from "@mui/material";

import styles from "./AttributeSelector.module.scss";
import { useSearchParams } from "react-router-dom";
import { useSelector } from "react-redux";
import { useState } from "react";

const AttributeSelector = ({
  attribute: initialAttribute,
  taxonset: initialTaxonset,
  setSelectedAttributeTaxonset,
}) => {
  const [searchParams, setSearchParams] = useSearchParams();

  const responseData = useSelector(
    (state) => state?.analysis?.availableAttributesTaxonsets?.data
  );

  const [attribute, setAttribute] = useState(initialAttribute);
  const [taxon, setTaxon] = useState(initialTaxonset);

  const handleAttributeChange = (e) => {
    const newAttribute = e.target.value;
    setAttribute(newAttribute);
    setTaxon("all"); // Reset taxonset when attribute changes
  };

  const handleTaxonChange = (e) => {
    setTaxon(e.target.value);
  };

  const handleApply = () => {
    const newParams = new URLSearchParams();

    // Preserve existing *_code keys and allow multiple values
    for (const [key, value] of searchParams.entries()) {
      if (key.endsWith("_code")) {
        newParams.append(key, value);
      }
    }

    newParams.set("attribute", attribute);
    newParams.set("taxonset", taxon);

    setSearchParams(newParams, { replace: true });

    setSelectedAttributeTaxonset({
      attribute,
      taxonset: taxon,
    });
  };

  const handleClear = () => {
    setAttribute("all");
    setTaxon("all");

    // Start fresh with URLSearchParams
    const newParams = new URLSearchParams();

    // Preserve existing *_code keys
    for (const [key, value] of searchParams.entries()) {
      if (key.endsWith("_code")) {
        newParams.append(key, value);
      }
    }
    newParams.set("attribute", "all");
    newParams.set("taxonset", "all");

    setSearchParams(newParams, { replace: true });

    setSelectedAttributeTaxonset({
      attribute: "all",
      taxonset: "all",
    });
  };

  return (
    <Box className={styles.container}>
      <Box className={styles.selectors}>
        <FormControl fullWidth size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Attribute</InputLabel>
          <Select
            value={responseData?.attributes ? attribute : ""}
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
          <Select
            value={responseData?.attributes ? taxon : ""}
            onChange={handleTaxonChange}
            label="Taxon Set"
          >
            <MenuItem value="">Select Taxon Set</MenuItem>
            {attribute &&
              responseData?.taxon_set?.[attribute]?.map((tx) => (
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
