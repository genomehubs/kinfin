import { useState, useRef, useEffect } from "react";
import styles from "./Sidebar.module.scss";
import { useTheme } from "../../../hooks/useTheme";
import { useNavigate, useParams } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";
import {
  Box,
  Menu,
  MenuItem,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
} from "@mui/material";

// MUI Icons
import MenuIcon from "@mui/icons-material/Menu";
import DownloadIcon from "@mui/icons-material/Download";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import LightModeIcon from "@mui/icons-material/LightMode";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import DeleteIcon from "@mui/icons-material/Delete";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";

import {
  renameConfig,
  deleteConfig,
  getValidProteomeIds,
  getBatchStatus,
  setSelectedClusterSet,
} from "../../../app/store/config/actions";

const downloadAsTSV = (analysis) => {
  const { name, config, sessionId } = analysis;
  if (!config || typeof config !== "object") return;

  const keys = Object.keys(config[0] || {});
  const tsvRows = [
    keys.join("\t"),
    ...config.map((row) =>
      keys.map((k) => (row[k] !== undefined ? row[k] : "")).join("\t")
    ),
  ];
  const blob = new Blob([tsvRows.join("\n")], {
    type: "text/tab-separated-values",
  });

  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${name || sessionId}.tsv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

const Sidebar = ({ open, setOpen }) => {
  const { theme, toggleTheme } = useTheme();
  const dispatch = useDispatch();
  const { sessionId } = useParams();
  const [modalOpen, setModalOpen] = useState(false);
  const [userName, setUserName] = useState("");
  const [nameError, setNameError] = useState("");
  const [anchorEl, setAnchorEl] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const navigate = useNavigate();
  const defaultItem = { label: "New Analysis", isNew: true };

  const analysisConfigs = useSelector(
    (state) => state?.config?.storeConfig?.data
  );
  const pollingLoadingBySessionId = useSelector(
    (state) => state.config.pollingLoadingBySessionId || {}
  );
  const selectedClusterSet = useSelector(
    (state) => state?.config?.selectedClusterSet
  );
  const analysisList = analysisConfigs && Object?.values(analysisConfigs);

  useEffect(() => {
    if (selectedClusterSet) {
      dispatch(getValidProteomeIds({ clusterId: selectedClusterSet }));
    }
  }, [selectedClusterSet]);

  const hasFetchedStatusRef = useRef(false);
  useEffect(() => {
    if (!hasFetchedStatusRef.current && analysisList?.length) {
      const sessionIds = analysisList.map((item) => item.sessionId);
      dispatch(getBatchStatus({ sessionIds }));
      hasFetchedStatusRef.current = true;
    }
  }, [analysisList]);

  const groupedAnalysis = analysisList?.reduce((acc, item) => {
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

  const handleSubmit = () => {
    if (!userName.trim()) {
      setNameError("Name is required.");
      return;
    }
    const payload = {
      newName: userName.trim(),
      sessionId: selectedItem?.sessionId,
    };
    dispatch(renameConfig(payload));
    setNameError("");
    setUserName("");
    setModalOpen(false);
  };

  const handleMenuOpen = (event, item) => {
    event.stopPropagation();
    setSelectedItem(item);
    setAnchorEl(event.currentTarget);
    setUserName(item.name);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  return (
    <>
      <div className={`${styles.sidebar} ${open ? "" : styles.closed}`}>
        <div className={styles.top}>
          <h2>KinFin</h2>
          <button className={styles.toggleBtn} onClick={() => setOpen(false)}>
            <MenuIcon />
          </button>
        </div>

        <div className={styles.menu}>
          <div className={styles.defaultSection}>
            <div
              onClick={() => {
                navigate(`/define-node-labels`);
                dispatch(setSelectedClusterSet(null));
              }}
              className={`${styles.menuItem} ${styles.newAnalysis}`}
            >
              <span className={styles.label}>{defaultItem.label}</span>
            </div>
          </div>

          <div className={styles.divider}></div>

          <div className={styles.otherSection}>
            {!analysisList?.length ? (
              <div className={styles.emptyState}>No saved analyses</div>
            ) : (
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
                        onClick={() => navigate(`/${item.sessionId}/dashboard`)}
                      >
                        <Box
                          sx={{
                            width: 12,
                            height: 12,
                            marginRight: "8px",
                            flexShrink: 0,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          {pollingLoadingBySessionId[item.sessionId] ? (
                            <CircularProgress size={10} thickness={8} />
                          ) : (
                            <Box
                              sx={{
                                width: 10,
                                height: 10,
                                borderRadius: "50%",
                                backgroundColor: item.status
                                  ? "#2ecc71"
                                  : "#ee2f42",
                              }}
                            />
                          )}
                        </Box>
                        <span className={styles.label}>{item.name}</span>
                        <IconButton
                          size="small"
                          onClick={(e) => handleMenuOpen(e, item)}
                        >
                          <MoreHorizIcon fontSize="small" />
                        </IconButton>
                      </div>
                    ))}
                  </div>
                )
              )
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
            setModalOpen(true);
            handleMenuClose();
          }}
        >
          <EditOutlinedIcon fontSize="small" sx={{ mr: 1 }} /> Rename
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

      {/* MUI Dialog for Rename */}
      <Dialog open={modalOpen} onClose={() => setModalOpen(false)} fullWidth>
        <DialogTitle>Rename Analysis</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Enter a name for this analysis"
            type="text"
            fullWidth
            variant="outlined"
            value={userName}
            error={!!nameError}
            helperText={nameError}
            onChange={(e) => {
              setUserName(e.target.value);
              if (nameError) setNameError("");
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setModalOpen(false);
              setUserName("");
              setNameError("");
            }}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} variant="contained">
            Submit
          </Button>
        </DialogActions>
      </Dialog>
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
              dispatch(deleteConfig(selectedItem?.sessionId));
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
