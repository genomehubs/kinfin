import {
  Button,
  ButtonGroup,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
} from "@mui/material";
import React, { useEffect, useMemo, useState } from "react";

const CustomisationDialog = ({
  open,
  onClose,
  onApply,
  selectedCodes,
  columnDescriptions = [],
  title = "Customisation",
}) => {
  const [localSelectedCodes, setLocalSelectedCodes] = useState(selectedCodes);

  useEffect(() => {
    setLocalSelectedCodes(selectedCodes);
  }, [selectedCodes]);

  const handleCheckboxChange = (code) => {
    setLocalSelectedCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const handleSelectAll = () => {
    setLocalSelectedCodes(columnDescriptions.map((c) => c.code));
  };

  const handleDeselectAll = () => {
    setLocalSelectedCodes([]);
  };

  const handleSelectDefaults = () => {
    setLocalSelectedCodes(
      columnDescriptions.filter((col) => col.isDefault).map((col) => col.code)
    );
  };

  const defaultList = useMemo(() => {
    return columnDescriptions
      .filter((col) => col.isDefault)
      .map((col) => col.code);
  }, [columnDescriptions]);

  const currentSelectedStatus = useMemo(() => {
    if (!localSelectedCodes || localSelectedCodes.length === 0) {
      return "none";
    }
    if (localSelectedCodes.length === columnDescriptions.length) {
      return "all";
    }
    if (
      localSelectedCodes.length === defaultList.length &&
      localSelectedCodes.every((code) => defaultList.includes(code))
    ) {
      return "default";
    }
    return "some";
  }, [localSelectedCodes, columnDescriptions, defaultList]);

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="lg">
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        {/* Select / Deselect All Actions */}
        <div style={{ display: "flex", gap: "12px", marginBottom: "12px" }}>
          <ButtonGroup>
            <Button
              variant={
                currentSelectedStatus === "all" ? "contained" : "outlined"
              }
              size="small"
              onClick={handleSelectAll}
            >
              All
            </Button>
            <Button
              variant={
                currentSelectedStatus === "none" ? "contained" : "outlined"
              }
              size="small"
              onClick={handleDeselectAll}
            >
              None
            </Button>
            <Button
              variant={
                currentSelectedStatus === "default" ? "contained" : "outlined"
              }
              size="small"
              onClick={handleSelectDefaults}
            >
              Defaults
            </Button>
          </ButtonGroup>
        </div>

        {/* Checkboxes Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "12px",
          }}
        >
          {columnDescriptions.map((item) => (
            <FormControlLabel
              key={item.code}
              control={
                <Checkbox
                  checked={localSelectedCodes.includes(item.code)}
                  onChange={() => handleCheckboxChange(item.code)}
                />
              }
              label={
                <div>
                  <strong>{item.alias || item.name}</strong>
                  <div style={{ fontSize: "0.8rem", color: "#666" }}>
                    {item.description}
                  </div>
                </div>
              }
            />
          ))}
        </div>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={() => onApply(localSelectedCodes)}
          variant="contained"
          color="primary"
        >
          Apply
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CustomisationDialog;
