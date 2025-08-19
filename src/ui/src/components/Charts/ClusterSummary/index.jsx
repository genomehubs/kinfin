import React, { useEffect, useMemo, useCallback } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useSearchParams } from "react-router-dom";
import { DataGrid } from "@mui/x-data-grid";
import styles from "./ClusterSummary.module.scss";
import { getClusterSummary } from "../../../app/store/analysis/slices/clusterSummarySlice";
import { v4 as uuidv4 } from "uuid";
import { updatePaginationParams } from "@/utils/urlPagination";

const pageSizeOptions = [5, 10, 25];

const ClusterSummary = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const clusterSummaryData = useSelector(
    (state) => state?.analysis?.clusterSummary?.data
  );
  const columnDescriptions = useSelector(
    (state) => state?.config?.columnDescriptions?.data || []
  );
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset || null
  );

  // Parse URL params
  const page = Math.max(
    parseInt(searchParams.get("CS_page") || "1", 10) - 1,
    0
  );
  const pageSize = Math.max(
    parseInt(searchParams.get("CS_pageSize") || "5", 10),
    1
  );
  const csCodes = useMemo(() => searchParams.getAll("CS_code"), [searchParams]);

  // Ensure defaults in URL
  useEffect(() => {
    const hasPage = searchParams.has("CS_page");
    const hasPageSize = searchParams.has("CS_pageSize");
    if (!hasPage || !hasPageSize) {
      setSearchParams(
        (prev) => {
          const newParams = new URLSearchParams(prev);
          if (!hasPage) {
            newParams.set("CS_page", "1");
          }
          if (!hasPageSize) {
            newParams.set("CS_pageSize", "5");
          }
          return newParams;
        },
        { replace: true }
      );
    }
  }, [searchParams, setSearchParams]);

  // Fetch data
  useEffect(() => {
    const payload = {
      page: page + 1, // backend is 1-based
      size: pageSize,
      attribute: selectedAttributeTaxonset?.attribute,
      CS_code: csCodes.length > 0 ? csCodes : undefined,
    };
    if (payload.attribute) {
      dispatch(getClusterSummary(payload));
    }
  }, [page, pageSize, csCodes, dispatch, selectedAttributeTaxonset]);

  const handlePaginationModelChange = useCallback(
    (newModel) => {
      updatePaginationParams(
        searchParams,
        setSearchParams,
        "CS",
        newModel.page,
        newModel.pageSize
      );
    },
    [searchParams, setSearchParams]
  );

  // 🔹 Flatten rows
  const processedRows = useMemo(() => {
    const rawData = clusterSummaryData?.data ?? {};
    return Object.values(rawData).map((row) => {
      const flat = { ...row };

      if (row.protein_counts && typeof row.protein_counts === "object") {
        Object.entries(row.protein_counts).forEach(([k, v]) => {
          flat[`protein_counts_${k}`] = v;
        });
        delete flat.protein_counts;
      }

      return {
        id: row.id || row.cluster_id || uuidv4(),
        ...flat,
      };
    });
  }, [clusterSummaryData]);

  // Row count
  const rowCount = useMemo(() => {
    if (clusterSummaryData?.total_entries != null) {
      return clusterSummaryData.total_entries;
    }
    if (
      clusterSummaryData?.total_pages &&
      clusterSummaryData?.entries_per_page
    ) {
      return (
        clusterSummaryData.total_pages * clusterSummaryData.entries_per_page
      );
    }
    return processedRows.length;
  }, [clusterSummaryData, processedRows]);

  // Map codes to field names
  const codeToFieldMap = useMemo(() => {
    return columnDescriptions.reduce((acc, col) => {
      acc[col.code] = col.name;
      return acc;
    }, {});
  }, [columnDescriptions]);

  // Base columns
  const baseColumns = [
    { field: "cluster_id", headerName: "Cluster ID", minWidth: 140 },
    {
      field: "cluster_protein_count",
      headerName: "Total Proteins",
      minWidth: 120,
    },
    {
      field: "protein_median_count",
      headerName: "Median Count",
      minWidth: 100,
    },
    { field: "TAXON_count", headerName: "TAXON Count", minWidth: 100 },
    { field: "attribute", headerName: "Attribute", minWidth: 120 },
    {
      field: "attribute_cluster_type",
      headerName: "Cluster Type",
      minWidth: 120,
    },
  ];

  // 🔹 Dynamically detect protein_counts_* fields
  const dynamicColumns = useMemo(() => {
    if (!processedRows.length) {
      return [];
    }

    const sampleRow = processedRows[0];

    return Object.keys(sampleRow)
      .filter((k) => k.startsWith("protein_counts_"))
      .map((field) => {
        const desc = columnDescriptions.find((c) => {
          if (!c.name.includes("X")) {
            return c.name === field;
          }
          const regex = new RegExp("^" + c.name.replace("X", "(.+)") + "$");
          return regex.test(field);
        });

        let headerName = field.replace("protein_counts_", "");

        if (desc && desc.name.includes("X")) {
          const regex = new RegExp("^" + desc.name.replace("X", "(.+)") + "$");
          const match = field.match(regex);

          if (match && match[1]) {
            headerName = desc.alias.replace("X", match[1]);
          }
        } else if (desc) {
          headerName = desc.alias || headerName;
        }
        headerName = headerName.replace(/_/g, " ");

        return {
          field,
          headerName,
          minWidth: 100,
        };
      });
  }, [processedRows, columnDescriptions]);

  // Merge base + dynamic columns
  const allColumns = useMemo(
    () => [...baseColumns, ...dynamicColumns],
    [baseColumns, dynamicColumns]
  );

  // 🔹 Filter columns by CS_code (with regex support for X)
  const filteredColumns = useMemo(() => {
    if (!csCodes || csCodes.length === 0) {
      return allColumns;
    }

    const patterns = csCodes
      .map((code) => codeToFieldMap[code])
      .filter(Boolean)
      .map((name) => {
        if (name.includes("X")) {
          return new RegExp("^" + name.replace("X", ".+") + "$");
        }
        return new RegExp("^" + name + "$");
      });

    return allColumns.filter((col) =>
      patterns.some((regex) => regex.test(col.field))
    );
  }, [csCodes, codeToFieldMap, allColumns]);

  return (
    <div
      style={{
        height: "50vh",
        width: "100%",
        overflowX: "auto",
        borderRadius: "12px",
      }}
    >
      <DataGrid
        rows={processedRows}
        columns={filteredColumns}
        paginationMode="server"
        paginationModel={{ page, pageSize }}
        onPaginationModelChange={handlePaginationModelChange}
        rowCount={rowCount}
        pageSizeOptions={pageSizeOptions}
        disableSelectionOnClick
        checkboxSelection={false}
        className={styles.listingTable}
        sx={{
          "& .MuiDataGrid-cell": {
            whiteSpace: "normal",
            wordBreak: "break-word",
            lineHeight: "1.4rem",
            alignItems: "start",
            p: "8px",
          },
          "& .MuiDataGrid-columnHeader": {
            whiteSpace: "normal",
            lineHeight: "normal",
          },
          "& .MuiDataGrid-columnHeaderTitle": {
            whiteSpace: "normal",
            wordBreak: "break-word",
            lineHeight: "normal",
            fontWeight: "bold",
          },
          "& .MuiDataGrid-columnHeaders": {
            backgroundColor: "#f5f5f5",
            borderBottom: "1px solid #cccccc",
            borderTop: "1px solid #cccccc",
          },
          "& .MuiDataGrid-row:nth-of-type(odd)": { backgroundColor: "#ffffff" },
          "& .MuiDataGrid-row:nth-of-type(even)": {
            backgroundColor: "#fafafa",
          },
        }}
      />
    </div>
  );
};

export default ClusterSummary;
