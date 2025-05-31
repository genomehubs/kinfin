import React, { useState, useRef, useEffect } from "react";
import styles from "./FileUpload.module.scss";
import { MdOutlineFileUpload } from "react-icons/md";
import * as XLSX from "xlsx";
import Papa from "papaparse";

const VALID_TAXONS = [
  "CBRIG",
  "DMEDI",
  "LSIGM",
  "AVITE",
  "CELEG",
  "EELAP",
  "OOCHE2",
  "OFLEX",
  "LOA2",
  "SLABI",
  "BMALA",
  "DIMMI",
  "WBANC2",
  "TCALL",
  "OOCHE1",
  "BPAHA",
  "OVOLV",
  "WBANC1",
  "LOA1",
];

const FileUpload = () => {
  const [selectedName, setSelectedName] = useState("");
  const [parsedData, setParsedData] = useState(null);
  const [viewMode, setViewMode] = useState("json");
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState("");
  const [invalidTaxons, setInvalidTaxons] = useState([]);
  const fileInputRef = useRef(null);

  const handleClick = () => {
    fileInputRef.current.click();
  };

  const validateTaxons = (data) => {
    if (!Array.isArray(data)) return [];
    const invalids = [];
    data.forEach((row, idx) => {
      const taxonKey = Object.keys(row).find(
        (k) => k.toLowerCase() === "taxon"
      );
      if (!taxonKey) return;
      const taxonValue = row[taxonKey];
      if (!VALID_TAXONS.includes(taxonValue)) {
        invalids.push({ index: idx, taxon: taxonValue });
      }
    });
    return invalids;
  };

  useEffect(() => {
    if (parsedData) {
      const invalids = validateTaxons(parsedData);
      setInvalidTaxons(invalids);
    } else {
      setInvalidTaxons([]);
    }
  }, [parsedData]);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setSelectedName(file.name);
    const ext = file.name.split(".").pop().toLowerCase();
    const reader = new FileReader();

    if (["xls", "xlsx"].includes(ext)) {
      reader.onload = (e) => {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: "array" });
        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        const json = XLSX.utils.sheet_to_json(sheet);
        setParsedData(json);
        setJsonText(JSON.stringify(json, null, 2));
        setJsonError("");
      };
      reader.readAsArrayBuffer(file);
    } else if (["csv", "tsv"].includes(ext)) {
      reader.onload = (e) => {
        const parsed = Papa.parse(e.target.result, {
          header: true,
          skipEmptyLines: true,
          delimiter: ext === "tsv" ? "\t" : ",",
        });
        setParsedData(parsed.data);
        setJsonText(JSON.stringify(parsed.data, null, 2));
        setJsonError("");
      };
      reader.readAsText(file);
    } else if (ext === "json") {
      reader.onload = (e) => {
        try {
          const json = JSON.parse(e.target.result);
          setParsedData(json);
          setJsonText(JSON.stringify(json, null, 2));
          setJsonError("");
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
    const value = e.target.value;
    setJsonText(value);

    try {
      const parsed = JSON.parse(value);
      setParsedData(parsed);
      setJsonError("");
    } catch {
      setJsonError("Invalid JSON syntax");
    }
  };

  const renderTable = () => {
    if (!Array.isArray(parsedData)) {
      return <p>Data is not in tabular format.</p>;
    }
    if (parsedData.length === 0) {
      return <p>No data to display.</p>;
    }
    const headers = Object.keys(parsedData[0]);
    const taxonKey = headers.find((h) => h.toLowerCase() === "taxon");

    return (
      <table className={styles.table}>
        <thead>
          <tr>
            {headers.map((head) => (
              <th key={head}>{head}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {parsedData.map((row, idx) => {
            const isInvalidTaxon = invalidTaxons.some(
              (item) => item.index === idx
            );
            return (
              <tr key={idx}>
                {headers.map((head) => (
                  <td
                    key={head}
                    className={
                      head === taxonKey && isInvalidTaxon
                        ? styles.invalidTaxonCell
                        : ""
                    }
                    contentEditable={true}
                    suppressContentEditableWarning={true}
                    onBlur={(e) => {
                      const newVal = e.target.textContent.trim();
                      const updatedData = [...parsedData];
                      updatedData[idx] = {
                        ...updatedData[idx],
                        [head]: newVal,
                      };
                      setParsedData(updatedData);
                      setJsonText(JSON.stringify(updatedData, null, 2));
                    }}
                  >
                    {row[head]?.toString() || ""}
                  </td>
                ))}
              </tr>
            );
          })}
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
          <h3>{selectedName || "Click box to upload"}</h3>
          <p>Maximum file size 10MB</p>
          <input
            type="file"
            ref={fileInputRef}
            accept=".csv,.tsv,.xls,.xlsx,.json"
            onChange={handleFileChange}
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
              {invalidTaxons.length > 0 && (
                <p className={styles.errorMessage}>
                  Invalid taxons found:{" "}
                  {invalidTaxons.map((i) => i.taxon).join(", ")}
                </p>
              )}
            </>
          )}

          {viewMode === "table" && (
            <>
              <h4>Table Preview:</h4>
              {renderTable()}
              {invalidTaxons.length > 0 && (
                <p className={styles.errorMessage}>
                  Please fix the highlighted taxons.
                </p>
              )}
            </>
          )}
        </div>
      )}
    </>
  );
};

export default FileUpload;
