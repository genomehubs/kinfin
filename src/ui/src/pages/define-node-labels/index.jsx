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
    // Simple validation: name must be non-empty
    if (!userName.trim()) {
      setNameError("Name is required.");
      return;
    }

    const id = uuidv4();
    const payload = {
      id,
      name: userName.trim(),
      jsonData: parsedData,
    };

    // Save into localStorage under a key, e.g. “kinfin_<UUID>”
    try {
      // localStorage.setItem(`kinfin_${id}`, JSON.stringify(payload));
      dispatch(AnalysisActions.storeConfig(payload));
      dispatch(AnalysisActions.initAnalysis({ config: parsedData }));
      // Optionally: you can also keep a running index or list of IDs;
      // e.g. push `kinfin_${id}` into an array in localStorage if you need to enumerate later.
    } catch (e) {
      console.error("Failed to save to localStorage:", e);
      alert(
        "Could not save data locally. Make sure storage quota is available."
      );
      return;
    }

    // Close modal after saving
    setModalOpen(false);
    alert(`Saved successfully! Your Analysis ID is:\n${id}`);
  };

  return (
    <AppLayout>
      <div className={styles.page}>
        {/* Pass a callback so FileUpload can “lift” its parsed JSON up into this state */}
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
          <div style={{ padding: "1rem" }}>
            <label htmlFor="analysis-name" style={{ fontWeight: 500 }}>
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
              style={{
                display: "block",
                width: "100%",
                padding: "8px",
                marginTop: "4px",
                marginBottom: nameError ? "4px" : "16px",
                border: nameError ? "1px solid #e74c3c" : "1px solid #ccc",
                borderRadius: "4px",
              }}
            />
            {nameError && (
              <p
                style={{
                  color: "#e74c3c",
                  margin: "0 0 16px 0",
                  fontSize: "0.875rem",
                }}
              >
                {nameError}
              </p>
            )}
            <button
              onClick={handleSubmit}
              style={{
                padding: "8px 16px",
                backgroundColor: "#3498db",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              Submit
            </button>
          </div>
        </Modal>
      </div>
    </AppLayout>
  );
};

export default DefineNodeLabels;
