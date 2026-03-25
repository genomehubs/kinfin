import { useCallback, useEffect, useRef, useState } from "react";
import { read, utils } from "xlsx";
import Papa from "papaparse";
import { skipToken } from "@reduxjs/toolkit/query/react";
import { useValidProteomeIds } from "#hooks/useValidProteomeIds.js";
import { validateDataset } from "#utils/validateDataset";

const SUPPORTED_EXTENSIONS = {
  xls: "excel",
  xlsx: "excel",
  csv: "csv",
  tsv: "tsv",
  json: "json",
};

export default function useFileUpload({
  onDataChange,
  setValidationErrors,
  disabled = false,
  clusterId = null,
} = {}) {
  const [selectedFileName, setSelectedFileName] = useState("");
  const [parsedData, setParsedData] = useState(null);
  const [viewMode, setViewMode] = useState("table");
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState("");

  const fileInputRef = useRef(null);
  const lastProcessedFileNameRef = useRef(null);

  const { data: validProteomeResponse, isError: validProteomeError } =
    useValidProteomeIds(
      clusterId ? { clusterId, page: 1, size: 100 } : skipToken,
    );
  const validProteomeIds =
    validProteomeResponse?.data ?? validProteomeResponse ?? {};

  useEffect(() => {
    if (validProteomeError && setValidationErrors) {
      setValidationErrors((prev) => ({
        ...prev,
        headers: [
          ...(prev.headers || []),
          "Failed to fetch valid proteome IDs for selected cluster",
        ],
      }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [validProteomeError]);

  const resetViewState = useCallback(() => {
    setJsonError("");
    setViewMode("table");
  }, []);

  const updateDataState = useCallback(
    (rawData) => {
      const { data: cleanedData, errors } = validateDataset(
        rawData,
        validProteomeIds,
      );
      setParsedData(cleanedData);
      setJsonText(JSON.stringify(cleanedData, null, 2));
      setValidationErrors?.(errors);
    },
    [validProteomeIds, setValidationErrors],
  );

  const tryParseJson = useCallback((text) => {
    try {
      return JSON.parse(text);
    } catch (err) {
      try {
        const sanitized = text
          .replace(/,\s*,/g, ",")
          .replace(/,\s*([}\]])/g, "$1");
        return JSON.parse(sanitized);
      } catch (err2) {
        throw err;
      }
    }
  }, []);

  useEffect(() => {
    onDataChange?.(parsedData);
  }, [parsedData, onDataChange]);

  const handleClick = () => fileInputRef.current?.click();
  const handleClickDisabled = () => {
    if (disabled) return;
    fileInputRef.current?.click();
  };

  const handleFileChange = useCallback(
    (event) => {
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
              const text = (e.target.result || "").replace(/^\uFEFF/, "");
              const json = tryParseJson(text);
              updateDataState(json);
            } catch {
              setParsedData([{ error: "Invalid JSON file" }]);
              setJsonText("");
              setJsonError("Invalid JSON file");
              setValidationErrors?.({ headers: [], rows: {} });
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
        // fallback
        reader.onload = (e) => {
          const text = (e.target.result || "").replace(/^\uFEFF/, "").trim();
          if (!text) {
            setParsedData([{ error: "Unsupported or empty file" }]);
            setJsonText("");
            return;
          }

          try {
            const parsed = tryParseJson(text);
            updateDataState(parsed);
            return;
          } catch (err) {
            // not JSON
          }

          try {
            const { data } = Papa.parse(text, {
              header: true,
              skipEmptyLines: true,
            });
            updateDataState(data);
            return;
          } catch (err) {
            setParsedData([{ error: "Unsupported file format" }]);
            setJsonText("");
          }
        };
        reader.readAsText(file);
      }
    },
    [resetViewState, tryParseJson, updateDataState, setValidationErrors],
  );

  // window focus fallback
  useEffect(() => {
    const onWindowFocus = () => {
      try {
        const input = fileInputRef.current;
        const f = input?.files?.[0];
        if (f && lastProcessedFileNameRef.current !== f.name) {
          const simulatedEvent = { target: { files: [f] } };
          handleFileChange(simulatedEvent);
          lastProcessedFileNameRef.current = f.name;
        }
      } catch (err) {
        // ignore
      }
    };

    window.addEventListener("focus", onWindowFocus);
    return () => window.removeEventListener("focus", onWindowFocus);
  }, [handleFileChange]);

  const handleJsonChange = useCallback(
    (e) => {
      const input = e.target.value;
      setJsonText(input);
      try {
        const parsed = JSON.parse(input);
        updateDataState(parsed);
        setJsonError("");
      } catch {
        setJsonError("Invalid JSON syntax");
      }
    },
    [updateDataState],
  );

  const handleCellEdit = useCallback(
    (e, rowIndex, header) => {
      const newValue = e.target.textContent.trim();
      const updated = [...(parsedData || [])];
      updated[rowIndex][header] = newValue;
      updateDataState(updated);
    },
    [parsedData, updateDataState],
  );

  const handleHeaderEdit = useCallback(
    (oldHeader, newHeader) => {
      if (!parsedData?.length || oldHeader === newHeader) return;

      const headers = Object.keys(parsedData[0]);
      const normalized = headers.map((h) => h.trim().toLowerCase());
      const newKey = newHeader.trim().toLowerCase();
      const oldKey = oldHeader.trim().toLowerCase();

      if (normalized.includes(newKey) && newKey !== oldKey) {
        setValidationErrors?.((prev) => ({
          ...prev,
          headers: [
            ...(prev.headers || []),
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
    },
    [parsedData, setValidationErrors, updateDataState],
  );

  return {
    selectedFileName,
    parsedData,
    viewMode,
    jsonText,
    jsonError,
    fileInputRef,
    handleClick,
    handleClickDisabled,
    handleFileChange,
    handleJsonChange,
    handleCellEdit,
    handleHeaderEdit,
    setViewMode,
    setParsedData,
  };
}
