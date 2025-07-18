import React, { useState } from "react";
import { Button, Menu, MenuItem, Typography, Box, Stack } from "@mui/material";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import { useSelector } from "react-redux";

export default function ClusterSetSelectionDropdown({ onChange }) {
  const [anchorEl, setAnchorEl] = useState(null);

  const clusteringSets =
    useSelector((state) => state?.config?.clusteringSets.data) || [];
  const selectedClusterSet = useSelector(
    (state) => state?.config?.selectedClusterSet
  );

  const selected = clusteringSets.find(
    (dataset) => dataset.id === selectedClusterSet
  );

  const handleOpen = (event) => setAnchorEl(event.currentTarget);
  const handleClose = () => setAnchorEl(null);

  const handleSelect = (dataset) => {
    onChange?.(dataset.id);
    handleClose();
  };

  return (
    <Box>
      <Button
        variant="outlined"
        onClick={handleOpen}
        endIcon={<ArrowDropDownIcon />}
        sx={{
          textTransform: "none",
          width: 420,
          justifyContent: "space-between",
        }}
      >
        <Stack alignItems="flex-start">
          <Typography variant="body1" fontWeight={600}>
            {selected?.name || "Select clustering dataset"}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {selected?.version && selected?.date
              ? `${selected.version} - ${selected.date}`
              : "Choose a dataset to begin analysis"}
          </Typography>
        </Stack>
      </Button>
      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleClose}>
        {clusteringSets.map((dataset) => (
          <MenuItem
            key={dataset.id}
            onClick={() => handleSelect(dataset)}
            sx={{ whiteSpace: "normal", alignItems: "flex-start" }}
            selected={selectedClusterSet === dataset.id}
          >
            <Stack spacing={0.5}>
              <Typography fontWeight={600}>{dataset.name}</Typography>
              <Typography variant="caption" color="text.secondary">
                {dataset.meta}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {dataset.description}
              </Typography>
            </Stack>
          </MenuItem>
        ))}
      </Menu>
    </Box>
  );
}
