import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Menu,
  MenuItem,
} from "@mui/material";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CircularProgress from "@mui/material/CircularProgress";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import DeleteIcon from "@mui/icons-material/Delete";
import DownloadIcon from "@mui/icons-material/Download";
import ErrorIcon from "@mui/icons-material/Error";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import LightModeIcon from "@mui/icons-material/LightMode";
import MenuIcon from "@mui/icons-material/Menu";
import PauseCircleIcon from "@mui/icons-material/PauseCircle";
import Tooltip from "@mui/material/Tooltip";
import { downloadBlobFile } from "#utils/downloadBlobFile";
import styles from "./Sidebar.module.scss";
import { useBatchStatus } from "#hooks/useBatchStatus.js";
import useConfigActions from "#hooks/useConfigActions";
import { useSelector } from "react-redux";
import { useTheme } from "#hooks/useTheme";

const downloadAsTSV = (analysis) => {
  const { name, config, sessionId } = analysis;
  if (!config || typeof config !== "object") {
    return;
  }

  const keys = Object.keys(config[0] || {});
  const tsvRows = [
    keys.join("\t"),
    ...config.map((row) =>
      keys.map((k) => (row[k] !== undefined ? row[k] : "")).join("\t"),
    ),
  ];
  const blob = new Blob([tsvRows.join("\n")], {
    type: "text/tab-separated-values",
  });

  downloadBlobFile(
    blob,
    `${name || sessionId}.tsv`,
    "text/tab-separated-values",
  );
};

const getStatusInfo = (status) => {
  switch (status) {
    case "error":
      return {
        color: "#ee2f42",
        icon: <ErrorIcon fontSize="inherit" />,
        label: "Error",
      };
    case "inactive":
      return {
        color: "#817b7b",
        icon: <PauseCircleIcon fontSize="inherit" />,
        label: "Inactive",
      };
    case "initialising":
      return {
        color: "#f39c12",
        icon: <HourglassEmptyIcon fontSize="inherit" />,
        label: "Initialising",
      };
    case "active":
      return {
        color: "#2ecc71",
        icon: <CheckCircleIcon fontSize="inherit" />,
        label: "Active",
      };
    default:
      return {
        color: "#bdc3c7",
        icon: <PauseCircleIcon fontSize="inherit" />,
        label: "Unknown",
      };
  }
};

const Sidebar = ({ open, setOpen }) => {
  const { theme, toggleTheme } = useTheme();
  const { deleteConfig } = useConfigActions();
  const { sessionId } = useParams();
  const [anchorEl, setAnchorEl] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const navigate = useNavigate();

  const analysisConfigs = useSelector((state) => state?.config?.data);
  const pollingLoadingBySessionId = useSelector(
    (state) => state?.config?.uiState?.pollingLoadingBySessionId || {},
  );

  const analysisList = analysisConfigs && Object?.values(analysisConfigs);

  const hasFetchedStatusRef = useRef(false);
  const [getBatchStatus] = useBatchStatus();
  useEffect(() => {
    if (!hasFetchedStatusRef.current && analysisList?.length) {
      const sessionIds = analysisList.map((item) => item.sessionId);
      getBatchStatus(sessionIds);
      hasFetchedStatusRef.current = true;
    }
  }, [analysisList, getBatchStatus]);

  const groupedAnalysis = analysisList?.reduce((acc, item) => {
    if (!item || !item.sessionId) return acc;
    const clusterId = item.clusterId || "unassigned";
    if (!acc[clusterId]) {
      acc[clusterId] = {
        clusterName: item.clusterName || "Unassigned Cluster",
        configs: [],
      };
    }
    acc[clusterId].configs.push(item);
    return acc;
  }, {});

  const handleMenuOpen = (event, item) => {
    event.stopPropagation();
    setSelectedItem(item);
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  return (
    <>
      <div className={`${styles.sidebar} ${open ? "" : styles.closed}`}>
        <div className={styles.menu}>
          <div className={styles.otherSection}>
            {analysisList?.length ? (
              Object.entries(groupedAnalysis).map(
                ([clusterId, { clusterName, configs }]) => (
                  <div key={clusterId} className={styles.clusterGroup}>
                    <div className={styles.clusterTitle}>{clusterName}</div>
                    {configs.map((item) => (
                      <div
                        key={item.sessionId}
                        className={`${styles.menuItem} ${
                          sessionId === item.sessionId ? styles.active : ""
                        }`}
                        onClick={() => navigate(`/${item.sessionId}`)}
                      >
                        <Box
                          sx={{
                            width: 16,
                            height: 16,
                            marginRight: "8px",
                            flexShrink: 0,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          {pollingLoadingBySessionId[item?.sessionId] ? (
                            <CircularProgress size={12} thickness={6} />
                          ) : (
                            (() => {
                              const { color, icon, label } = getStatusInfo(
                                item.status,
                              );
                              return (
                                <Tooltip title={label} arrow>
                                  <Box
                                    sx={{
                                      width: 16,
                                      height: 16,
                                      display: "flex",
                                      alignItems: "center",
                                      justifyContent: "center",
                                      color: color,
                                      "& svg": {
                                        color: color,
                                        fill: color,
                                      },
                                    }}
                                  >
                                    {icon}
                                  </Box>
                                </Tooltip>
                              );
                            })()
                          )}
                        </Box>
                        <span className={styles.label}>
                          {item.name || `Session ${item.sessionId}`}
                        </span>
                        <IconButton
                          size="small"
                          onClick={(e) => handleMenuOpen(e, item)}
                        >
                          <MenuIcon fontSize="small" />
                        </IconButton>
                      </div>
                    ))}
                  </div>
                ),
              )
            ) : (
              <div className={styles.emptyState}>No saved analyses</div>
            )}
          </div>
        </div>

        <div className={styles.bottom}>
          <div className={styles.themeTrigger} onClick={toggleTheme}>
            {theme === "dark" ? (
              <DarkModeIcon fontSize="small" />
            ) : (
              <LightModeIcon fontSize="small" />
            )}{" "}
            Theme
          </div>
        </div>
      </div>

      {/* MUI Menu for actions */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem
          onClick={() => {
            downloadAsTSV(selectedItem);
            handleMenuClose();
          }}
        >
          <DownloadIcon fontSize="small" sx={{ mr: 1 }} /> Download
        </MenuItem>
        <MenuItem
          onClick={() => {
            setDeleteDialogOpen(true);
            handleMenuClose();
          }}
        >
          <DeleteIcon fontSize="small" sx={{ mr: 1 }} /> Delete
        </MenuItem>
      </Menu>

      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle>Confirm Deletion</DialogTitle>
        <DialogContent>
          <p>
            Are you sure you want to delete{" "}
            <strong>{selectedItem?.name || "this analysis"}</strong>? This
            action cannot be undone.
          </p>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => {
              deleteConfig(selectedItem?.sessionId);
              setDeleteDialogOpen(false);
            }}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {!open && (
        <button className={styles.floatingToggle} onClick={() => setOpen(true)}>
          <MenuIcon />
        </button>
      )}
    </>
  );
};

export default Sidebar;
