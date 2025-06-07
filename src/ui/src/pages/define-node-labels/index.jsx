// src/pages/DefineNodeLabels/DefineNodeLabels.jsx
import React, { useState } from "react";
import { v4 as uuidv4 } from "uuid";
import AppLayout from "../../components/AppLayout";
import FileUpload from "../../components/FileUpload"; // adjust the path if needed
import Modal from "../../components/UIElements/Modal";
import styles from "./DefineNodeLabels.module.scss";
import { useDispatch, useSelector } from "react-redux";
import * as AnalysisActions from "../../app/store/kinfin/actions";

const DefineNodeLabels = () => {
  const dispatch = useDispatch();
  // State for parsed JSON data coming from FileUpload
  const [parsedData, setParsedData] = useState(null);

  // State to control modal visibility
  const [modalOpen, setModalOpen] = useState(false);
  // State to hold the “name” input inside the modal
  const [userName, setUserName] = useState("");
  // State to show any validation error in the modal
  const [nameError, setNameError] = useState("");

  // When the “Initialize Kinfin Analysis” button is clicked:
  const openModal = () => {
    if (!parsedData) {
      alert("Please upload and validate your JSON first.");
      return;
    }
    setUserName("");
    setNameError("");
    setModalOpen(true);
  };

  // Handle submission inside the modal:
  const handleSubmit = () => {
    if (!userName.trim()) {
      setNameError("Name is required.");
      return;
    }
    const payload = {
      name: userName.trim(),
      config: parsedData,
    };
    dispatch(AnalysisActions.initAnalysis(payload));
    setModalOpen(false);
  };

  return (
    <AppLayout>
      <div className={styles.page}>
        <FileUpload onDataChange={setParsedData} />

        <div className={styles.bottomSection}>
          <button className={styles.initButton} onClick={openModal}>
            Initialize Kinfin Analysis
          </button>
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
      </div>
    </AppLayout>
  );
};

export default DefineNodeLabels;
