import React, { useState, useRef, useEffect } from "react";
import styles from "./FileUpload.module.scss";
import { MdOutlineFileUpload } from "react-icons/md";
import { read, utils } from "xlsx";
import Papa from "papaparse";
import { useSelector } from "react-redux";
import { validateDataset } from "../../utilis/validateDataset";

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

  const renderTable = () => {
    if (!Array.isArray(parsedData)) {
      return <p>Data is not in tabular format.</p>;
    }
    if (parsedData.length === 0) {
      return <p>No data to display.</p>;
    }

    const headers = Object.keys(parsedData[0]);

    return (
      <table className={styles.table}>
        <thead>
          <tr>
            {headers.map((head) => {
              const hasHeaderError = validationErrors.headers.some((error) =>
                error.includes(head)
              );
              const headerErrorMsg = validationErrors.headers.find((error) => {
                const normalizedHead = head.trim().toLowerCase();
                return error.toLowerCase().includes(`'${normalizedHead}'`);
              });

              return (
                <th
                  className={hasHeaderError ? styles.invalidHeader : ""}
                  title={hasHeaderError ? headerErrorMsg : ""}
                  key={head}
                >
                  <div
                    contentEditable={true}
                    suppressContentEditableWarning={true}
                    onBlur={(e) => {
                      const newHeader = e.target.textContent.trim();
                      if (newHeader && newHeader !== head) {
                        handleHeaderEdit(head, newHeader);
                      }
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        e.target.blur();
                      }
                    }}
                    style={{
                      minWidth: "100px",
                      padding: "4px",
                      outline: "none",
                      borderRadius: "2px",
                      cursor: "text",
                    }}
                  >
                    {head}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {parsedData.map((row, idx) => (
            <tr key={idx}>
              {headers.map((head) => {
                const cellError = validationErrors.rows?.[idx]?.[head] || "";
                return (
                  <td
                    key={head}
                    className={cellError ? styles.invalidCell : ""}
                    title={cellError}
                    contentEditable={true}
                    suppressContentEditableWarning={true}
                    onBlur={(e) => {
                      const newVal = e.target.textContent.trim();
                      const updatedData = [...parsedData];
                      updatedData[idx][head] = newVal;
                      setParsedData(updatedData);
                      setJsonText(JSON.stringify(updatedData, null, 2));
                      setValidationErrors(
                        validateDataset(updatedData, VALID_PROTEOME_IDS)
                      );
                    }}
                  >
                    {row[head]?.toString() || ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  return (
    <>
      {!parsedData && (
        <div className={styles.uploadBox} onClick={handleClick}>
          <p className={styles.icon}>
            <MdOutlineFileUpload />
          </p>
          <h3>{selectedName || "Click box to upload config"}</h3>
          <p>Maximum file size 10MB</p>
          <input
            type="file"
            ref={fileInputRef}
            accept=".csv,.tsv,.xls,.xlsx,.json"
            onChange={handleFileChange}
            hidden
          />
        </div>
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
            <>
              <h4>Parsed JSON (editable):</h4>
              <textarea
                className={styles.jsonTextarea}
                value={jsonText}
                onChange={handleJsonChange}
                spellCheck={false}
              />
              {jsonError && <p className={styles.errorMessage}>{jsonError}</p>}
            </>
          )}

          {viewMode === "table" && (
            <>
              <h4>Table Preview:</h4>
              {renderTable()}
            </>
          )}
          {validationErrors.headers.length > 0 && (
            <div className={styles.errorMessage}>
              <p>Header validation issues:</p>
              <ul>
                {validationErrors.headers.map((msg, i) => (
                  <li key={i}>{msg}</li>
                ))}
              </ul>
            </div>
          )}
          {Object.keys(validationErrors.rows).length > 0 && (
            <div className={styles.errorMessage}>
              <p>Row validation issues:</p>
              <ul>
                {Object.entries(validationErrors.rows).map(
                  ([rowIndex, rowErrors]) => (
                    <li key={rowIndex}>
                      Row {parseInt(rowIndex, 10) + 1}:
                      <ul>
                        {Object.entries(rowErrors).map(
                          ([field, errorMsg], i) => (
                            <li key={i}>
                              <strong>{field}:</strong> {errorMsg}
                            </li>
                          )
                        )}
                      </ul>
                    </li>
                  )
                )}
              </ul>
            </div>
          )}
        </div>
      )}
    </>
  );
};

export default FileUpload;
