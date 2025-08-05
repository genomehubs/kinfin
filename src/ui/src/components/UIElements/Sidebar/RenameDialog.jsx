import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
} from "@mui/material";

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
    setValue(e.target.value);
    if (error) {
      setError("");
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
      onSubmit();
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
          helperText={error}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCancel}>Cancel</Button>
        <Button onClick={onSubmit} variant="contained">
          Submit
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default RenameDialog;
