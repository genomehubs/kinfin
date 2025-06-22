import React, { useState } from "react";
import { Button, Menu, MenuItem, Typography, Box, Stack } from "@mui/material";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import { useDispatch, useSelector } from "react-redux";
import { setSelectedClusterSet } from "../../app/store/config/actions";

export default function ClusterSetSelectionDropdown() {
  const [anchorEl, setAnchorEl] = useState(null);
  const [selected, setSelected] = useState(null);
  const clusteringSets =
    useSelector((state) => state?.config?.clusteringSets.data) || [];

  const dispatch = useDispatch();
  const handleOpen = (event) => setAnchorEl(event.currentTarget);
  const handleClose = () => setAnchorEl(null);

  const handleSelect = (dataset) => {
    setSelected(dataset);
    dispatch(setSelectedClusterSet(dataset.id));
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
          width: 300,
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
