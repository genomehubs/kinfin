import React, { useState } from "react";
import AppLayout from "../../components/AppLayout";
import FileUpload from "../../components/FileUpload"; // adjust the path if needed
import Modal from "../../components/UIElements/Modal";
import styles from "./DefineNodeLabels.module.scss";
import { useDispatch } from "react-redux";
import { initAnalysis } from "../../app/store/config/actions";

const DefineNodeLabels = () => {
  const dispatch = useDispatch();
  const [parsedData, setParsedData] = useState(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [userName, setUserName] = useState("");
  const [nameError, setNameError] = useState("");

  const openModal = () => {
    if (!parsedData) {
      alert("Please upload and validate your JSON first.");
      return;
    }
    setUserName("");
    setNameError("");
    setModalOpen(true);
  };

  const handleSubmit = () => {
    if (!userName.trim()) {
      setNameError("Name is required.");
      return;
    }
    const payload = {
      name: userName.trim(),
      config: parsedData,
    };
    dispatch(initAnalysis(payload));
    setModalOpen(false);
  };

  return (
    <AppLayout>
      <div className={styles.page}>
        <FileUpload onDataChange={setParsedData} />

        {parsedData && (
          <div className={styles.bottomSection}>
            <button className={styles.initButton} onClick={openModal}>
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
