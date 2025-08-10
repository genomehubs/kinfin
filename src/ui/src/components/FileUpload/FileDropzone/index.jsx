import React, { useEffect } from "react";
import FileUploadOutlinedIcon from "@mui/icons-material/FileUploadOutlined";
import styles from "./FileDropZone.module.scss";

const FileDropZone = ({ onClick, selectedName, inputRef, onChange }) => {
  useEffect(() => {
    const preventDefaults = (e) => {
      e.preventDefault();
      e.stopPropagation();
    };

    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) =>
      window.addEventListener(eventName, preventDefaults)
    );

    return () => {
      ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) =>
        window.removeEventListener(eventName, preventDefaults)
      );
    };
  }, []);

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();

    const file = e.dataTransfer.files?.[0];
    if (file) {
      const simulatedEvent = { target: { files: [file] } };
      onChange(simulatedEvent);
    }
  };

  return (
    <div
      className={styles.uploadBox}
      onClick={onClick}
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
    >
      <p className={styles.icon}>
        <FileUploadOutlinedIcon fontSize="large" />
      </p>
      <h3>{selectedName || "Click or drag a file to upload config"}</h3>
      <p>Maximum file size 10MB</p>
      <input
        type="file"
        ref={inputRef}
        accept=".csv,.tsv,.xls,.xlsx,.json"
        onChange={onChange}
        hidden
      />
    </div>
  );
};

export default FileDropZone;
