import React, { useState, useRef, useEffect } from "react";
import styles from "./FileUpload.module.scss";
import { read, utils } from "xlsx";
import Papa from "papaparse";
import { useSelector } from "react-redux";
import FileDropZone from "./FileDropzone";
import ValidationErrors from "./ValidationErrors";
import { validateDataset } from "../../utilis/validateDataset";
import DataTable from "./DataTable";
import JsonEditor from "./JsonEditor";

const FileUpload = ({
  onDataChange,
  validationErrors,
  setValidationErrors,
}) => {
  const [selectedName, setSelectedName] = useState("");
  const [parsedData, setParsedData] = useState(null);
  const [viewMode, setViewMode] = useState("json");
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState("");

  const fileInputRef = useRef(null);

  const validProteomeIds = useSelector(
    (state) => state.config.validProteomeIds.data
  );
  const VALID_PROTEOME_IDS = Object.keys(validProteomeIds || {});

  const handleClick = () => fileInputRef.current.click();

  useEffect(() => {
    if (onDataChange) onDataChange(parsedData);
  }, [parsedData, onDataChange]);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setSelectedName(file.name);
    const ext = file.name.split(".").pop().toLowerCase();
    const reader = new FileReader();

    const processJson = (data) => {
      setParsedData(data);
      setJsonText(JSON.stringify(data, null, 2));
      setJsonError("");
      setValidationErrors(validateDataset(data, VALID_PROTEOME_IDS));
    };

    if (["xls", "xlsx"].includes(ext)) {
      reader.onload = (e) => {
        const data = new Uint8Array(e.target.result);
        const workbook = read(data, { type: "array" });
        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        const json = utils.sheet_to_json(sheet);
        processJson(json);
      };
      reader.readAsArrayBuffer(file);
    } else if (["csv", "tsv"].includes(ext)) {
      reader.onload = (e) => {
        const parsed = Papa.parse(e.target.result, {
          header: true,
          skipEmptyLines: true,
          delimiter: ext === "tsv" ? "\t" : ",",
        });
        processJson(parsed.data);
      };
      reader.readAsText(file);
    } else if (ext === "json") {
      reader.onload = (e) => {
        try {
          const json = JSON.parse(e.target.result);
          processJson(json);
        } catch {
          setParsedData([{ error: "Invalid JSON file" }]);
          setJsonText("");
          setJsonError("Invalid JSON file");
          setValidationErrors({ headers: [], rows: {} });
        }
      };
      reader.readAsText(file);
    } else {
      setParsedData([{ error: "Unsupported file format" }]);
      setJsonText("");
      setJsonError("");
    }

    setViewMode("json");
  };

  const handleJsonChange = (e) => {
    const { value } = e.target;
    setJsonText(value);
    try {
      const parsed = JSON.parse(value);
      setParsedData(parsed);
      setValidationErrors(validateDataset(parsed, VALID_PROTEOME_IDS));
      setJsonError("");
    } catch {
      setJsonError("Invalid JSON syntax");
    }
  };
  const handleCellEdit = (e, idx, head) => {
    const newVal = e.target.textContent.trim();
    const updatedData = [...parsedData];
    updatedData[idx][head] = newVal;
    setParsedData(updatedData);
    setJsonText(JSON.stringify(updatedData, null, 2));
    setValidationErrors(validateDataset(updatedData, VALID_PROTEOME_IDS));
  };

  const handleHeaderEdit = (oldHeader, newHeader) => {
    if (!parsedData || !Array.isArray(parsedData) || oldHeader === newHeader) {
      return;
    }

    const currentHeaders = Object.keys(parsedData[0] || {});
    const normalized = currentHeaders.map((h) => h.trim().toLowerCase());

    if (
      normalized.includes(newHeader.trim().toLowerCase()) &&
      oldHeader.trim().toLowerCase() !== newHeader.trim().toLowerCase()
    ) {
      setValidationErrors((prev) => ({
        ...prev,
        headers: [
          ...prev.headers,
          `Cannot rename '${oldHeader}' to '${newHeader}' — header already exists.`,
        ],
      }));
      return;
    }

    const updatedData = parsedData.map((row) => {
      const newRow = {};
      Object.keys(row).forEach((key) => {
        if (key === oldHeader) {
          newRow[newHeader] = row[oldHeader];
        } else {
          newRow[key] = row[key];
        }
      });
      return newRow;
    });

    setParsedData(updatedData);
    setJsonText(JSON.stringify(updatedData, null, 2));
    setValidationErrors(validateDataset(updatedData, VALID_PROTEOME_IDS));
  };

  return (
    <>
      {!parsedData && (
        <FileDropZone
          onClick={handleClick}
          selectedName={selectedName}
          inputRef={fileInputRef}
          onChange={handleFileChange}
        />
      )}

      {parsedData && (
        <div className={styles.preview}>
          <div className={styles.toggleButtons}>
            <button
              className={viewMode === "json" ? styles.active : ""}
              onClick={() => setViewMode("json")}
            >
              JSON View
            </button>
            <button
              className={viewMode === "table" ? styles.active : ""}
              onClick={() => setViewMode("table")}
            >
              Table View
            </button>
          </div>

          {viewMode === "json" && (
            <JsonEditor
              jsonText={jsonText}
              onChange={handleJsonChange}
              jsonError={jsonError}
            />
          )}

          {viewMode === "table" && (
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
