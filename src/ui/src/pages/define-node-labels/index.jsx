import React, { useEffect, useState } from "react";
import AppLayout from "../../components/AppLayout";
import FileUpload from "../../components/FileUpload";
import Modal from "../../components/UIElements/Modal";
import styles from "./DefineNodeLabels.module.scss";
import { useDispatch, useSelector } from "react-redux";
import {
  initAnalysis,
  getClusteringSets,
  setSelectedClusterSet,
} from "../../app/store/config/actions";
import ClusterSetSelectionDropdown from "../../components/ClusterSetSelectionDropdown";
import { useNavigate } from "react-router-dom";

const DefineNodeLabels = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();

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
  const [pendingClusterId, setPendingClusterId] = useState(null);
  const [confirmClusterChangeOpen, setConfirmClusterChangeOpen] =
    useState(false);

  useEffect(() => {
    dispatch(getClusteringSets());
  }, []);
  useEffect(() => {
    dispatch(setSelectedClusterSet(null));
  }, []);

  const openModal = () => {
    if (!parsedData) {
      alert("Please upload and validate your config file first.");
      return;
    }
    setUserName("");
    setNameError("");
    setModalOpen(true);
  };

  const cancelAnalysis = () => {
    setParsedData(null);
    setValidationErrors({ headers: [], rows: {} });
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
      clusterName: selectedCluster?.name || "",
      navigate,
    };

    dispatch(initAnalysis(payload));
    setModalOpen(false);
  };

  const handleClusterSetChange = (newClusterId) => {
    if (parsedData) {
      setPendingClusterId(newClusterId);
      setConfirmClusterChangeOpen(true);
    } else {
      console.log("jkdcbjkdsbcdjksbc khd d 1");
      dispatch(setSelectedClusterSet(newClusterId));
    }
  };

  const confirmClusterChange = () => {
    if (pendingClusterId) {
      console.log("first");
      dispatch(setSelectedClusterSet(pendingClusterId));
      setParsedData(null);
      setValidationErrors({ headers: [], rows: {} });
      setResetKey((prev) => prev + 1);
      setPendingClusterId(null);
    }
    setConfirmClusterChangeOpen(false);
  };

  const cancelClusterChange = () => {
    setPendingClusterId(null);
    setConfirmClusterChangeOpen(false);
  };

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
            {" "}
            <ClusterSetSelectionDropdown onChange={handleClusterSetChange} />
          </div>
        </div>

        {/* Step 2 */}
        <div
          className={`${styles.workflowStep} ${
            !selectedClusterSet ? styles.disabled : ""
          }`}
        >
          <div className={styles.stepHeader}>
            <span className={styles.stepNumber}>2</span>
            <h3>Upload Configuration</h3>
          </div>
          <FileUpload
            key={resetKey}
            disabled={!selectedClusterSet}
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
        </div>

        {/* Modal for Analysis Name */}
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
                if (nameError) setNameError("");
              }}
              className={`${styles.input} ${nameError ? styles.error : ""}`}
            />

            {nameError && <p className={styles.errorMessage}>{nameError}</p>}

            <button onClick={handleSubmit} className={styles.submitButton}>
              Submit
            </button>
          </div>
        </Modal>

        {/* Confirm Cluster Change */}
        <Modal
          isOpen={confirmClusterChangeOpen}
          onClose={cancelClusterChange}
          title="Change Clustering Dataset?"
        >
          <div className={styles.container}>
            <p style={{ marginBottom: "1rem" }}>
              Changing the dataset will clear your uploaded configuration. Are
              you sure you want to continue?
            </p>
            <div className={styles.bottomSection}>
              <button
                className={styles.cancelButton}
                onClick={cancelClusterChange}
              >
                Cancel
              </button>
              <button
                className={styles.submitButton}
                onClick={confirmClusterChange}
              >
                Yes, Change It
              </button>
            </div>
          </div>
        </Modal>
      </div>
    </AppLayout>
  );
};

export default DefineNodeLabels;
