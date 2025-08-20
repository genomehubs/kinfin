import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Checkbox,
  Button,
} from "@mui/material";

const CustomisationDialog = ({
  open,
  onClose,
  onApply,
  selectedCodes,
  onCheckboxChange,
  columnDescriptions = [],
  title = "Customisation",
}) => {
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="lg">
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
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
                  checked={selectedCodes.includes(item.code)}
                  onChange={() => onCheckboxChange(item.code)}
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
        <Button onClick={onApply} variant="contained" color="primary">
          Apply
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CustomisationDialog;
