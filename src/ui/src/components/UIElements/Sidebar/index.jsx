import { useState, useRef, useEffect } from "react";
import styles from "./Sidebar.module.scss";
import { FiMenu, FiDownload } from "react-icons/fi";
import { GoKebabHorizontal } from "react-icons/go";
import { FaSun, FaMoon } from "react-icons/fa";
import { useTheme } from "../../../hooks/useTheme";
import { useNavigate, useParams } from "react-router-dom";
import Tooltip from "rc-tooltip";
import "rc-tooltip/assets/bootstrap.css";
import { AiFillDelete } from "react-icons/ai";
import Modal from "../Modal";

import { MdOutlineEdit } from "react-icons/md";
import { useDispatch, useSelector } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";
import {
  renameConfig,
  deleteConfig,
  getValidProteomeIds,
  getBatchStatus,
} from "../../../app/store/config/actions";
import { Box } from "@mui/material";

const downloadAsTSV = (analysis) => {
  const { name, config, sessionId } = analysis;

  if (!config || typeof config !== "object") {
    return;
  }

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
  const [sessionIdClicked, setSessionIdClicked] = useState("");
  const [visibleTooltip, setVisibleTooltip] = useState(null);
  const navigate = useNavigate();
  const defaultItem = { label: "New Analysis", isNew: true };
  const analysisConfigs = useSelector(
    (state) => state?.config?.storeConfig?.data
  );
  const pollingLoadingBySessionId = useSelector(
    (state) => state.config.pollingLoadingBySessionId || {}
  );
  const analysisList = analysisConfigs && Object?.values(analysisConfigs);
  const tooltipRef = useRef(null);
  const selectedClusterSet = useSelector(
    (state) => state?.config?.selectedClusterSet
  );

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
      sessionId: sessionIdClicked,
    };

    dispatch(renameConfig(payload));
    setNameError("");
    setUserName("");
    setModalOpen(false);
  };

  return (
    <>
      <div className={`${styles.sidebar} ${open ? "" : styles.closed}`}>
        <div className={styles.top}>
          <h2>KinFin</h2>
          <button className={styles.toggleBtn} onClick={() => setOpen(false)}>
            <FiMenu />
          </button>
        </div>

        <div className={styles.menu}>
          {/* Default item */}
          <div className={styles.defaultSection}>
            <div
              onClick={() => navigate(`/define-node-labels`)}
              className={`${styles.menuItem} ${styles.newAnalysis}`}
            >
              <span className={styles.label}>{defaultItem.label}</span>
            </div>
          </div>

          <div className={styles.divider}></div>

          {/* Analysis list */}
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
                          visibleTooltip === item.sessionId ||
                          sessionId === item.sessionId
                            ? styles.active
                            : ""
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
                        <div className={styles.refContainer} ref={tooltipRef}>
                          <Tooltip
                            placement="rightTop"
                            styles={{ root: { pointerEvents: "auto" } }}
                            onVisibleChange={(visible) => {
                              if (!visible) setVisibleTooltip(null);
                            }}
                            trigger={["click"]}
                            overlay={
                              <div className={styles.tooltipContent}>
                                <div
                                  className={styles.tooltipItem}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    downloadAsTSV(item);
                                  }}
                                >
                                  <FiDownload /> Download
                                </div>
                                <div
                                  className={styles.tooltipItem}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setModalOpen(true);
                                  }}
                                >
                                  <MdOutlineEdit /> Rename
                                </div>
                                <div
                                  className={styles.tooltipItem}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    dispatch(deleteConfig(sessionIdClicked));
                                  }}
                                >
                                  <AiFillDelete /> Delete
                                </div>
                              </div>
                            }
                            visible={visibleTooltip === item.sessionId}
                            showArrow={false}
                            defaultVisible={false}
                          >
                            <GoKebabHorizontal
                              className={styles.downloadIcon}
                              onClick={(e) => {
                                e.stopPropagation();
                                setSessionIdClicked(item.sessionId);
                                setUserName(item.name);
                                setVisibleTooltip((prev) =>
                                  prev === item.sessionId
                                    ? null
                                    : item.sessionId
                                );
                              }}
                            />
                          </Tooltip>
                        </div>
                      </div>
                    ))}
                  </div>
                )
              )
            )}
          </div>
        </div>

        <div className={styles.bottom}>
          <Tooltip
            placement="rightTop"
            trigger={["click"]}
            overlay={
              <div className={styles.tooltipTheme}>
                <div className={styles.themeHeading}>
                  <p>Switch Appearance</p>
                  <FaMoon />
                </div>
                <div className={styles.toggleWrapper} onClick={toggleTheme}>
                  <span className={styles.toggleText}>Dark Mode</span>
                  <div
                    className={`${styles.toggle} ${
                      theme === "dark" ? styles.active : ""
                    }`}
                  >
                    <div className={styles.icon}>
                      {theme === "dark" ? <FaMoon /> : <FaSun />}
                    </div>
                  </div>
                </div>
              </div>
            }
            showArrow={false}
          >
            <div className={styles.themeTrigger}>
              {theme === "dark" ? <FaMoon /> : <FaSun />} Theme
            </div>
          </Tooltip>
        </div>
      </div>
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Initialize Analysis"
      >
        <div className={styles.container}>
          <label htmlFor="analysis-name" className={styles.label}>
            Enter a name for this analysis:
          </label>
          <input
            id="analysis-name"
            type="text"
            value={userName}
            onChange={(e) => {
              setUserName(e.target.value);
              if (nameError) {
                setNameError("");
              }
            }}
            className={`${styles.input} ${nameError ? styles.error : ""}`}
          />
          {nameError && <p className={styles.errorMessage}>{nameError}</p>}
          <button onClick={handleSubmit} className={styles.submitButton}>
            Submit
          </button>
        </div>
      </Modal>
      {!open && (
        <button className={styles.floatingToggle} onClick={() => setOpen(true)}>
          <FiMenu />
        </button>
      )}
    </>
  );
};

export default Sidebar;
