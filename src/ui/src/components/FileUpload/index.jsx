import React from "react";
import DataTable from "./DataTable";
import FileDropZone from "./FileDropzone";
import JsonEditor from "./JsonEditor";
import ValidationErrors from "./ValidationErrors";
import styles from "./FileUpload.module.scss";
import useFileUpload from "#hooks/useFileUpload";

const SUPPORTED_EXTENSIONS = {
  xls: "excel",
  xlsx: "excel",
  csv: "csv",
  tsv: "tsv",
  json: "json",
};

const FileUpload = ({
  onDataChange,
  validationErrors,
  setValidationErrors,
  disabled = false,
  clusterId = null,
}) => {
  const {
    selectedFileName,
    parsedData,
    viewMode,
    jsonText,
    jsonError,
    fileInputRef,
    handleClickDisabled,
    handleFileChange,
    handleJsonChange,
    handleCellEdit,
    handleHeaderEdit,
    setViewMode,
  } = useFileUpload({ onDataChange, setValidationErrors, disabled, clusterId });

  return (
    <>
      {!parsedData && (
        <FileDropZone
          onClick={handleClickDisabled}
          selectedName={selectedFileName}
          inputRef={fileInputRef}
          onChange={handleFileChange}
          disabled={disabled}
        />
      )}

      {parsedData && (
        <div className={styles.preview}>
          <div className={styles.toggleButtons}>
            {["table", "json"].map((mode) => (
              <button
                key={mode}
                className={viewMode === mode ? styles.active : ""}
                onClick={() => setViewMode(mode)}
              >
                {mode === "json" ? "JSON View" : "Table View"}
              </button>
            ))}
          </div>

          {viewMode === "json" ? (
            <JsonEditor
              jsonText={jsonText}
              onChange={handleJsonChange}
              jsonError={jsonError}
            />
          ) : (
            <>
              <h4>Table Preview:</h4>
              <DataTable
                parsedData={parsedData}
                validationErrors={validationErrors}
                handleHeaderEdit={handleHeaderEdit}
                handleCellEdit={handleCellEdit}
              />
            </>
          )}

          <ValidationErrors validationErrors={validationErrors} />
        </div>
      )}
    </>
  );
};

export default FileUpload;
