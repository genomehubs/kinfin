import {
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Button as MuiButton,
} from "@mui/material";
import React, { useState, useCallback } from "react";

import AppLayout from "#components/AppLayout";
import ClusterSetSelectionDropdown from "#components/ClusterSetSelectionDropdown";
import FileUpload from "#components/FileUpload";
import RenameDialog from "#components/UIElements/Sidebar/RenameDialog";
import styles from "./DefineNodeLabels.module.scss";
import { useClusteringSets } from "#hooks/useClusteringSets";
import { useInitAnalysis } from "#hooks/useInitAnalysis";
import { useNavigate } from "react-router-dom";

// Direct imports of RTK Query hooks

const DefineNodeLabelsPage = () => {
  const navigate = useNavigate();

  // Fetch clustering sets
  const {
    data: clusteringSets = [],
    isLoading,
    error,
  } = useClusteringSets({ page: 1, size: 50 });

  // Initialize analysis mutation
  const {
    initAnalysis,
    isLoading: isInitializing,
    error: initError,
  } = useInitAnalysis();

  // Local UI state
  const [selectedClusterSet, setSelectedClusterSet] = useState(null);
  const [parsedData, setParsedData] = useState(null);
  const [validationErrors, setValidationErrors] = useState({
    headers: [],
    rows: {},
  });
  const [modalOpen, setModalOpen] = useState(false);
  const [userName, setUserName] = useState("");
  const [nameError, setNameError] = useState("");
  const [resetKey, setResetKey] = useState(0);
  const [pendingClusterId, setPendingClusterId] = useState(null);
  const [confirmClusterChangeOpen, setConfirmClusterChangeOpen] =
    useState(false);

  const openModal = useCallback(() => {
    if (!parsedData) {
      alert("Please upload and validate your config file first.");
      return;
    }
    setUserName("");
    setNameError("");
    setModalOpen(true);
  }, [parsedData]);

  const cancelAnalysis = useCallback(() => {
    setParsedData(null);
    setValidationErrors({ headers: [], rows: {} });
    setResetKey((prev) => prev + 1);
    setModalOpen(false);
    setUserName("");
    setNameError("");
    setSelectedClusterSet(null);
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!userName.trim()) {
      setNameError("Name is required.");
      return;
    }
    setNameError("");
    setNameError("");
    try {
      const result = await initAnalysis({
        config: parsedData,
        clusterId: selectedClusterSet,
        isAdvanced: false,
        name: userName,
      }).unwrap();

      // result may be the API response or an envelope { data: ... }
      const sessionId = result?.sessionId ?? result?.data?.sessionId;

      if (sessionId) {
        navigate(`/${sessionId}/`);
        setModalOpen(false);
      } else {
        setNameError("Initialization succeeded but no session id returned");
      }
    } catch (err) {
      console.error("Init analysis error:", err);
      setNameError(
        err?.data?.message || err?.message || "Failed to initialize analysis",
      );
    }
  }, [userName, parsedData, selectedClusterSet, initAnalysis, navigate]);

  const handleClusterSetChange = useCallback(
    (newClusterId) => {
      if (parsedData) {
        setPendingClusterId(newClusterId);
        setConfirmClusterChangeOpen(true);
      } else {
        setSelectedClusterSet(newClusterId);
      }
    },
    [parsedData],
  );

  const confirmClusterChange = useCallback(() => {
    if (pendingClusterId) {
      setSelectedClusterSet(pendingClusterId);
      setParsedData(null);
      setValidationErrors({ headers: [], rows: {} });
      setResetKey((prev) => prev + 1);
      setPendingClusterId(null);
    }
    setConfirmClusterChangeOpen(false);
  }, [pendingClusterId]);

  const cancelClusterChange = useCallback(() => {
    setPendingClusterId(null);
    setConfirmClusterChangeOpen(false);
  }, []);

  if (isLoading) {
    return (
      <AppLayout>
        <div>Loading clustering sets...</div>
      </AppLayout>
    );
  }

  if (error) {
    return (
      <AppLayout>
        <div style={{ color: "red" }}>
          Error loading clustering sets: {JSON.stringify(error)}
        </div>
      </AppLayout>
    );
  }

  if (initError) {
    return (
      <AppLayout>
        <div style={{ color: "red" }}>
          Error initializing analysis: {JSON.stringify(initError)}
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className={styles.page}>
        {/* Step 1 */}
        <div className={styles.workflowStep}>
          <div className={styles.stepHeader}>
            <span className={styles.stepNumber}>1</span>
            <h3>Select Clustering Dataset</h3>
          </div>
          <div className={styles.clusterSetParent}>
            <ClusterSetSelectionDropdown
              onChange={handleClusterSetChange}
              clusteringSets={clusteringSets}
              selectedClusterSet={selectedClusterSet}
            />
          </div>
        </div>

        {/* Step 2 */}
        <div
          className={`${styles.workflowStep} ${
            selectedClusterSet ? "" : styles.disabled
          }`}
        >
          <div className={styles.stepHeader}>
            <span className={styles.stepNumber}>2</span>
            <h3>Upload Configuration</h3>
          </div>
          <FileUpload
            key={resetKey}
            disabled={!selectedClusterSet}
            clusterId={selectedClusterSet}
            setValidationErrors={setValidationErrors}
            validationErrors={validationErrors}
            onDataChange={setParsedData}
          />
        </div>

        {/* Step 3 */}
        <div
          className={`${styles.workflowStep} ${
            selectedClusterSet ? "" : styles.disabled
          }`}
        >
          <div className={styles.stepHeader}>
            <span className={styles.stepNumber}>3</span>
            <h3>Initialize KinFin Analysis</h3>
          </div>

          <div className={styles.bottomSection}>
            <button className={styles.cancelButton} onClick={cancelAnalysis}>
              Cancel Analysis
            </button>
            <button
              disabled={
                isInitializing ||
                validationErrors.headers.length > 0 ||
                Object.keys(validationErrors.rows).length > 0
              }
              className={styles.initButton}
              onClick={openModal}
              title={
                validationErrors.headers.length > 0 ||
                Object.keys(validationErrors.rows).length > 0
                  ? "Please fix validation issues"
                  : ""
              }
            >
              {isInitializing
                ? "Initializing..."
                : "Initialize KinFin Analysis"}
            </button>
          </div>
        </div>

        <RenameDialog
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          onSubmit={handleSubmit}
          value={userName}
          setValue={setUserName}
          error={nameError}
          setError={setNameError}
          title="Name Analysis"
        />

        <Dialog
          open={confirmClusterChangeOpen}
          onClose={cancelClusterChange}
          fullWidth
        >
          <DialogTitle>Change Clustering Dataset?</DialogTitle>
          <DialogContent>
            <div className={styles.container}>
              <p style={{ marginBottom: "1rem" }}>
                Changing the dataset will clear your uploaded configuration. Are
                you sure you want to continue?
              </p>
            </div>
          </DialogContent>
          <DialogActions>
            <MuiButton onClick={cancelClusterChange}>Cancel</MuiButton>
            <MuiButton onClick={confirmClusterChange} variant="contained">
              Yes, Change It
            </MuiButton>
          </DialogActions>
        </Dialog>
      </div>
    </AppLayout>
  );
};

export default React.memo(DefineNodeLabelsPage);
