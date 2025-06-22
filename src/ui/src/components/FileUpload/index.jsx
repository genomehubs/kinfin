import React, { useState, useRef, useEffect, useCallback } from "react";
import styles from "./FileUpload.module.scss";
import { MdOutlineFileUpload } from "react-icons/md";
import { read, utils } from "xlsx";
import Papa from "papaparse";
import { useSelector } from "react-redux";
import FileDropZone from "./FileDropzone";
import ValidationErrors from "./ValidationErrors";
import { validateDataset } from "../../utilis/validateDataset";
import DataTable from "./DataTable";
import JsonEditor from "./JsonEditor";

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
}) => {
  const [selectedFileName, setSelectedFileName] = useState("");
  const [parsedData, setParsedData] = useState(null);
  const [viewMode, setViewMode] = useState("json");
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState("");

  const fileInputRef = useRef(null);

  const validProteomeIds = useSelector(
    (state) => state.config.validProteomeIds.data
  );
  console.log("🚀 ~ validProteomeIds:", validProteomeIds);

  const resetViewState = useCallback(() => {
    setJsonError("");
    setViewMode("json");
  }, []);

  const updateDataState = useCallback(
    (rawData) => {
      const { data: cleanedData, errors } = validateDataset(
        rawData,
        validProteomeIds
      );
      setParsedData(cleanedData);
      setJsonText(JSON.stringify(cleanedData, null, 2));
      setValidationErrors(errors);
    },
    [validProteomeIds, setValidationErrors]
  );

  useEffect(() => {
    onDataChange?.(parsedData);
  }, [parsedData, onDataChange]);

  const handleClick = () => fileInputRef.current?.click();

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const ext = file.name.split(".").pop().toLowerCase();
    const fileType = SUPPORTED_EXTENSIONS[ext];

    setSelectedFileName(file.name);
    resetViewState();

    const reader = new FileReader();

    const handleParse = {
      excel: () => {
        reader.onload = (e) => {
          const workbook = read(new Uint8Array(e.target.result), {
            type: "array",
          });
          const sheet = workbook.Sheets[workbook.SheetNames[0]];
          updateDataState(utils.sheet_to_json(sheet));
        };
        reader.readAsArrayBuffer(file);
      },
      csv: () => parseDelimited(file, ","),
      tsv: () => parseDelimited(file, "\t"),
      json: () => {
        reader.onload = (e) => {
          try {
            const json = JSON.parse(e.target.result);
            updateDataState(json);
          } catch {
            setParsedData([{ error: "Invalid JSON file" }]);
            setJsonText("");
            setJsonError("Invalid JSON file");
            setValidationErrors({ headers: [], rows: {} });
          }
        };
        reader.readAsText(file);
      },
    };

    const parseDelimited = (file, delimiter) => {
      reader.onload = (e) => {
        const { data } = Papa.parse(e.target.result, {
          header: true,
          skipEmptyLines: true,
          delimiter,
        });
        updateDataState(data);
      };
      reader.readAsText(file);
    };

    if (handleParse[fileType]) {
      handleParse[fileType]();
    } else {
      setParsedData([{ error: "Unsupported file format" }]);
      setJsonText("");
    }
  };

  const handleJsonChange = (e) => {
    const input = e.target.value;
    setJsonText(input);
    try {
      const parsed = JSON.parse(input);
      updateDataState(parsed);
      setJsonError("");
    } catch {
      setJsonError("Invalid JSON syntax");
    }
  };

  const handleCellEdit = (e, rowIndex, header) => {
    const newValue = e.target.textContent.trim();
    const updated = [...parsedData];
    updated[rowIndex][header] = newValue;
    updateDataState(updated);
  };

  const handleHeaderEdit = (oldHeader, newHeader) => {
    if (!parsedData?.length || oldHeader === newHeader) return;

    const headers = Object.keys(parsedData[0]);
    const normalized = headers.map((h) => h.trim().toLowerCase());
    const newKey = newHeader.trim().toLowerCase();
    const oldKey = oldHeader.trim().toLowerCase();

    if (normalized.includes(newKey) && newKey !== oldKey) {
      setValidationErrors((prev) => ({
        ...prev,
        headers: [
          ...prev.headers,
          `Cannot rename '${oldHeader}' to '${newHeader}' — header already exists.`,
        ],
      }));
      return;
    }

    const updated = parsedData.map((row) => {
      const newRow = {};
      for (const key in row) {
        newRow[key === oldHeader ? newHeader : key] = row[key];
      }
      return newRow;
    });

    updateDataState(updated);
  };

  return (
    <>
      {!parsedData && (
        <FileDropZone
          onClick={handleClick}
          selectedName={selectedFileName}
          inputRef={fileInputRef}
          onChange={handleFileChange}
        />
      )}

      {parsedData && (
        <div className={styles.preview}>
          <div className={styles.toggleButtons}>
            {["json", "table"].map((mode) => (
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
