const isAlphaNum = (val) => /^[a-zA-Z0-9_]+$/.test(val);
const isValidValue = (val) =>
  typeof val === "string" && /^[a-zA-Z0-9_]+$/.test(val);

export const validateDataset = (data, validProteomeMap) => {
  const errors = {
    headers: [],
    rows: {},
  };

  if (!Array.isArray(data) || data.length === 0) {
    return { data: [], errors };
  }

  const validProteomes = Object.keys(validProteomeMap || {});
  const taxonToCanonical = {};

  for (const [canonical, info] of Object.entries(validProteomeMap)) {
    if (info?.taxon_id) taxonToCanonical[info.taxon_id] = canonical;
    if (info?.species) taxonToCanonical[info.species.toLowerCase()] = canonical;
  }

  const headersRaw = Object.keys(data[0]);
  const headersLC = headersRaw.map((h) => h.toLowerCase());

  if (!headersLC.includes("taxon")) {
    errors.headers.push("Missing required 'taxon' column");
  }

  const seenHeaders = new Set();
  headersLC.forEach((h) => {
    if (seenHeaders.has(h)) {
      errors.headers.push(`Duplicate column header (case-insensitive): ${h}`);
    }
    seenHeaders.add(h);
  });

  headersRaw.forEach((h) => {
    if (!isAlphaNum(h)) {
      errors.headers.push(
        `Invalid column header '${h}': Must be alphanumeric with underscores`
      );
    }
  });

  const columnValues = {};
  headersRaw.forEach((h) => (columnValues[h] = new Set()));

  const taxonCol = headersRaw.find((h) => h.toLowerCase() === "taxon");
  const seenTaxons = new Set();
  const validatedData = [];

  data.forEach((row, rowIndex) => {
    const newRow = { ...row };

    headersRaw.forEach((col) => {
      const val = row[col];

      if (val == null || val === "") {
        errors.rows[rowIndex] ??= {};
        errors.rows[rowIndex][col] = "Missing value";
      } else if (!isValidValue(val.toString())) {
        errors.rows[rowIndex] ??= {};
        errors.rows[rowIndex][col] =
          "Invalid value: must be alphanumeric or underscore";
      } else {
        columnValues[col].add(val.toString().toLowerCase());
      }
    });

    const taxonRaw = row[taxonCol];
    let canonicalId = null;

    if (taxonRaw) {
      const taxon = taxonRaw.toString();
      if (validProteomes.includes(taxon)) {
        canonicalId = taxon;
      } else {
        canonicalId = taxonToCanonical[taxon.toLowerCase()] ?? null;
      }

      if (!canonicalId) {
        errors.rows[rowIndex] ??= {};
        errors.rows[rowIndex][
          "taxon"
        ] = `Invalid taxon or unrecognized ID: ${taxon}`;
      } else if (seenTaxons.has(canonicalId)) {
        errors.rows[rowIndex] ??= {};
        errors.rows[rowIndex]["taxon"] = `Duplicate taxon: ${canonicalId}`;
      } else {
        seenTaxons.add(canonicalId);
        newRow[taxonCol] = canonicalId;
      }
    }

    validatedData.push(newRow);
  });

  Object.entries(columnValues).forEach(([col, valueSet]) => {
    if (valueSet.size < 2) {
      errors.headers.push(`Column '${col}' has less than 2 distinct values`);
    }
  });

  return { data: validatedData, errors };
};
