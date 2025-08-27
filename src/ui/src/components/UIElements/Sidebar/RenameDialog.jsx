import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from "@mui/material";

import React from "react";

const RenameDialog = ({
  open,
  onClose,
  onSubmit,
  value,
  setValue,
  error,
  setError,
  title = "Rename Analysis",
  label = "Enter a name for this analysis",
}) => {
  const handleInputChange = (e) => {
    const newValue = e.target.value;
    setValue(newValue);
    // Only allow alphanumeric and underscore
    if (/^[A-Za-z0-9_]*$/.test(newValue)) {
      setError("");
    } else {
      setError("Only alphanumeric characters and underscores are allowed.");
    }
  };

  const handleCancel = () => {
    onClose();
    setValue("");
    setError("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      // Only submit if no error
      if (!error) {
        onSubmit();
      }
    } else if (e.key === "Escape") {
      handleCancel();
    }
  };

  return (
    <Dialog open={open} onClose={handleCancel} fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          margin="dense"
          label={label}
          type="text"
          fullWidth
          variant="outlined"
          value={value}
          error={!!error}
          helperText={error || " "}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCancel}>Cancel</Button>
        <Button
          onClick={onSubmit}
          variant="contained"
          disabled={!!error || !value}
        >
          Submit
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default RenameDialog;
