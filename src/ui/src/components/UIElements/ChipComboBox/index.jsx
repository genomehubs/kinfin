import React, { useState, useMemo, useEffect } from "react";
import { TextField, Autocomplete, Chip } from "@mui/material";
import { useSearchParams } from "react-router-dom";

export default function ChipComboBox({ options = [] }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedItems, setSelectedItems] = useState([]);

  // Remove already-selected items from dropdown
  const availableOptions = useMemo(() => {
    return options.filter(
      (opt) => !selectedItems.some((item) => item.code === opt.code)
    );
  }, [options, selectedItems]);

  // Update ?codes= query param when selected items change
  useEffect(() => {
    const codes = selectedItems.map((item) => item.code);
    if (codes.length > 0) {
      searchParams.set("codes", codes.join(","));
    } else {
      searchParams.delete("codes");
    }
    setSearchParams(searchParams);
  }, [selectedItems]);

  return (
    <Autocomplete
      multiple
      options={availableOptions}
      getOptionLabel={(option) =>
        `${option.name}${option.description ? " - " + option.description : ""}`
      }
      isOptionEqualToValue={(option, value) => option.code === value.code}
      value={selectedItems}
      onChange={(event, newValue) => setSelectedItems(newValue)}
      renderTags={(value, getTagProps) =>
        value.map((option, index) => (
          <Chip
            key={option.code}
            variant="outlined"
            label={option.name}
            {...getTagProps({ index })}
          />
        ))
      }
      renderInput={(params) => (
        <TextField
          {...params}
          variant="outlined"
          label="Select Items"
          placeholder="Start typing..."
        />
      )}
    />
  );
}
