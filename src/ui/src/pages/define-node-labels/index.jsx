import React, { useEffect, useState } from "react";
import AppLayout from "../../components/AppLayout";
import FileUpload from "../../components/FileUpload"; // adjust the path if needed
import Modal from "../../components/UIElements/Modal";
import styles from "./DefineNodeLabels.module.scss";
import { useDispatch, useSelector } from "react-redux";
import {
  initAnalysis,
  getClusteringSets,
} from "../../app/store/config/actions";
import ClusterSetSelectionDropdown from "../../components/ClusterSetSelectionDropdown";
import { useNavigate } from "react-router-dom";

// MUI components
import Backdrop from "@mui/material/Backdrop";
import CircularProgress from "@mui/material/CircularProgress";

const DefineNodeLabels = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const pollingLoading = useSelector((state) => state.config.pollingLoading);
  const selectedClusterSet = useSelector(
    (state) => state?.config?.selectedClusterSet
  );
  const clusteringSets =
    useSelector((state) => state?.config?.clusteringSets.data) || [];

  const [parsedData, setParsedData] = useState(null);
  const [validationErrors, setValidationErrors] = useState({
    headers: [],
    rows: {},
  });
  const [modalOpen, setModalOpen] = useState(false);
  const [userName, setUserName] = useState("");
  const [nameError, setNameError] = useState("");
  const [resetKey, setResetKey] = useState(0);

  const openModal = () => {
    if (!parsedData) {
      alert("Please upload and validate your JSON first.");
      return;
    }
    setUserName("");
    setNameError("");
    setModalOpen(true);
  };
  const cancelAnalysis = () => {
    setParsedData(null);
    setValidationErrors({
      headers: [],
      rows: {},
    });

    setResetKey((prev) => prev + 1);

    setModalOpen(false);
    setUserName("");
    setNameError("");
  };

  const handleSubmit = () => {
    if (!userName.trim()) {
      setNameError("Name is required.");
      return;
    }
    const selectedCluster = clusteringSets.find(
      (set) => set.id === selectedClusterSet
    );

    const payload = {
      name: userName.trim(),
      config: parsedData,
      clusterId: selectedClusterSet,
      clusterName: selectedCluster.name || "",
      navigate,
    };
    dispatch(initAnalysis(payload));
    setModalOpen(false);
  };
  useEffect(() => {
    dispatch(getClusteringSets());
  }, []);

  return (
    <AppLayout>
      <div className={styles.page}>
        <ClusterSetSelectionDropdown />
        <FileUpload
          key={resetKey}
          setValidationErrors={setValidationErrors}
          validationErrors={validationErrors}
          onDataChange={setParsedData}
        />

        {parsedData && (
          <div className={styles.bottomSection}>
            <button className={styles.cancelButton} onClick={cancelAnalysis}>
              Cancel Analysis
            </button>
            <button
              disabled={
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
              Initialize Kinfin Analysis
            </button>
          </div>
        )}

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
      </div>
    </AppLayout>
  );
};

export default DefineNodeLabels;
