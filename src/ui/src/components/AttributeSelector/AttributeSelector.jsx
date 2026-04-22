import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
} from "@mui/material";
import { useEffect, useRef, useState } from "react";

import styles from "./AttributeSelector.module.scss";
import { toCamelCase } from "#utils/changeCase.js";
import { useGetAvailableAttributesTaxonsetsQuery } from "#store/api";
import { useSearchParams } from "react-router-dom";

const AttributeSelector = ({
  attribute: initialAttribute,
  taxonset: initialTaxonset,
  setSelectedAttributeTaxonset,
  sessionId,
  isLoading = false,
}) => {
  const [searchParams, setSearchParams] = useSearchParams();

  const { data: responseData, refetch } =
    useGetAvailableAttributesTaxonsetsQuery(sessionId, {
      skip: !sessionId,
      // Refetch when new data is available (e.g., analysis completes)
      refetchOnMountOrArgChange: true,
    });

  const prevIsLoadingRef = useRef(isLoading);
  const prevSessionIdRef = useRef(sessionId);

  // Refetch attributes/taxonsets when analysis completes (isLoading becomes false)
  useEffect(() => {
    if (prevIsLoadingRef.current && !isLoading && sessionId) {
      refetch();
    }
    prevIsLoadingRef.current = isLoading;
  }, [isLoading, sessionId, refetch]);

  // When sessionId changes, reset local state until new options load
  useEffect(() => {
    if (sessionId && sessionId !== prevSessionIdRef.current) {
      setAttribute("");
      setTaxon("");
      prevSessionIdRef.current = sessionId;
    }
  }, [sessionId]);

  // Unwrap the nested data structure from ResponseSchema
  // API returns: { status, message, data: { attributes, taxon_set } }
  // But ResponseSchema wraps it again, so we get: { data: { attributes, taxon_set } }
  // Need to extract the actual attributes and taxon_set
  const innerData =
    responseData?.data &&
    typeof responseData.data === "object" &&
    "attributes" in responseData.data
      ? responseData.data
      : responseData?.data?.data || responseData;

  // Deduplicate attributes and normalize keys for display
  const uniqueAttributes = Array.from(
    new Set(
      innerData?.attributes && Array.isArray(innerData.attributes)
        ? innerData.attributes
        : [],
    ),
  );

  const taxonsets = innerData?.taxon_set || [];

  // Initialize with empty string - will be updated when data loads
  const [attribute, setAttribute] = useState("");
  const [taxon, setTaxon] = useState("");

  // When options become available, update empty values to use initial values or "all"
  // Also sync when initialAttribute/initialTaxonset props change (e.g. on session switch)
  useEffect(() => {
    // Update attribute if options are available
    if (uniqueAttributes.length > 0) {
      setAttribute(initialAttribute ?? "all");
    }

    // Update taxon if options are available
    if (taxonsets.length > 0) {
      setTaxon(initialTaxonset ?? "all");
    }
  }, [
    uniqueAttributes.length,
    taxonsets.length,
    initialAttribute,
    initialTaxonset,
  ]);

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
      {isLoading && (
        <Box
          sx={{
            marginBottom: 2,
            padding: 1,
            backgroundColor: "#f5f5f5",
            borderRadius: 1,
          }}
        >
          <em>
            Attributes and taxon sets will be available once analysis completes.
          </em>
        </Box>
      )}
      <Box className={styles.selectors}>
        <FormControl fullWidth size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Attribute</InputLabel>
          <Select
            value={attribute ?? ""}
            onChange={handleAttributeChange}
            label="Attribute"
            disabled={!uniqueAttributes.length}
          >
            <MenuItem value="">Select Attribute</MenuItem>
            {uniqueAttributes.map((attr) => (
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
            value={taxon ?? ""}
            onChange={handleTaxonChange}
            label="Taxon Set"
          >
            <MenuItem value="">Select Taxon Set</MenuItem>
            {attribute &&
              (
                innerData?.taxonSet?.[toCamelCase(attribute)] ??
                innerData?.taxon_set?.[attribute] ??
                innerData?.taxon_set?.[toCamelCase(attribute)] ??
                []
              ).map((tx) => (
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
          disabled={isLoading}
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
          disabled={isLoading}
        >
          Clear
        </Button>
      </Box>
    </Box>
  );
};

export default AttributeSelector;
