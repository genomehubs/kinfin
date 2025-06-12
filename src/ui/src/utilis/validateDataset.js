// validateDataset.js

const isAlphaNum = (val) => /^[a-zA-Z0-9_]+$/.test(val);
const isValidValue = (val) =>
  typeof val === "string" && /^[a-zA-Z0-9_]+$/.test(val);

export const validateDataset = (data, validProteomes) => {
  const errors = {
    headers: [],
    rows: {}, // { rowIndex: { colName: 'error message' } }
  };

  if (!Array.isArray(data) || data.length === 0) {
    return errors;
  }

  const headersRaw = Object.keys(data[0]);
  const headersLC = headersRaw.map((h) => h.toLowerCase());

  // Check required column
  if (!headersLC.includes("taxon")) {
    errors.headers.push("Missing required 'taxon' column");
  }

  // Check duplicate headers (case-insensitive)
  const seen = new Set();
  headersLC.forEach((h) => {
    if (seen.has(h)) {
      errors.headers.push(
        `Duplicate column header found (case-insensitive): ${h}`
      );
    }
    seen.add(h);
  });

  // Validate header names
  headersRaw.forEach((h) => {
    if (!isAlphaNum(h)) {
      errors.headers.push(
        `Invalid column header '${h}': Must be alphanumeric with underscores`
      );
    }
  });

  const columnValues = {};
  headersRaw.forEach((h) => (columnValues[h] = new Set()));

  data.forEach((row, rowIndex) => {
    headersRaw.forEach((col) => {
      const val = row[col];

      if (!val || val.toString().trim() === "") {
        if (!errors.rows[rowIndex]) errors.rows[rowIndex] = {};
        errors.rows[rowIndex][col] = "Missing value";
      } else if (!isValidValue(val.toString())) {
        if (!errors.rows[rowIndex]) errors.rows[rowIndex] = {};
        errors.rows[rowIndex][col] =
          "Invalid value: must be alphanumeric or underscore";
      } else {
        columnValues[col].add(val.toString().toLowerCase());
      }
    });

    const taxon = row[headersRaw.find((h) => h.toLowerCase() === "taxon")];
    if (taxon && !validProteomes.includes(taxon)) {
      if (!errors.rows[rowIndex]) errors.rows[rowIndex] = {};
      errors.rows[rowIndex]["taxon"] = `Invalid taxon: ${taxon}`;
    }
  });

  // Column distinct value check
  Object.entries(columnValues).forEach(([col, valueSet]) => {
    if (valueSet.size < 2) {
      errors.headers.push(`Column '${col}' has less than 2 distinct values`);
    }
  });

  return errors;
};
