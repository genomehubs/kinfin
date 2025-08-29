import React, { useCallback, useEffect, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";

import { DataGrid } from "@mui/x-data-grid";
import { getClusterSummary } from "../../../app/store/analysis/slices/clusterSummarySlice";
import styles from "./ClusterSummary.module.scss";
import { updatePaginationParams } from "@/utils/urlPagination";
import { useSearchParams } from "react-router-dom";
import { v4 as uuidv4 } from "uuid";

const pageSizeOptions = [5, 10, 25];

const ClusterSummary = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const clusterSummaryData = useSelector(
    (state) => state?.analysis?.clusterSummary?.data
  );
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset || null
  );
  const columnDescriptions = useSelector((state) =>
    (state?.config?.columnDescriptions?.data || []).filter(
      (col) => col.file === "*.cluster_summary.txt"
    )
  );

  const attribute = selectedAttributeTaxonset?.attribute || "null";

  const page = Math.max(
    parseInt(searchParams.get("CS_page") || "1", 10) - 1,
    0
  );
  const pageSize = Math.max(
    parseInt(searchParams.get("CS_pageSize") || "5", 10),
    1
  );

  const csCodes = useMemo(() => {
    if (!searchParams.has("CS_code")) {
      return columnDescriptions
        .filter((col) => col.isDefault)
        .map((col) => col.code);
    }
    return searchParams.getAll("CS_code");
  }, [searchParams, columnDescriptions]);

  useEffect(() => {
    if (!attribute) {
      return;
    }

    dispatch(
      getClusterSummary({
        attribute,
        page: page + 1,
        size: pageSize,
        CS_code: csCodes.length > 0 ? csCodes : undefined,
      })
    );
  }, [dispatch, attribute, page, pageSize, csCodes]);

  // Flatten rows
  const rowsData = useMemo(() => {
    if (!clusterSummaryData?.data) {
      return { rows: [], rowCount: 0 };
    }

    const rows = Object.values(clusterSummaryData.data).map((row) => ({
      id: row.id || row.cluster_id || uuidv4(),
      ...row,
    }));

    const totalRows =
      clusterSummaryData.total_entries ??
      (clusterSummaryData.total_pages && clusterSummaryData.entries_per_page
        ? clusterSummaryData.total_pages * clusterSummaryData.entries_per_page
        : rows.length);

    return { rows, rowCount: totalRows };
  }, [clusterSummaryData]);

  // Columns from columnDescriptions handling X placeholders
  const defaultColumns = useMemo(() => {
    if (!rowsData.rows.length) {
      return [];
    }

    return columnDescriptions
      .map((col) => {
        if (!col.name.includes("X")) {
          return {
            field: col.name,
            headerName: col.alias || col.name,
            minWidth: 120,
          };
        }

        // Handle X in name by matching against actual row keys
        const sampleRow = rowsData.rows[0];
        const regex = new RegExp("^" + col.name.replace("X", "(.+)") + "$");
        return Object.keys(sampleRow)
          .filter((k) => regex.test(k))
          .map((field) => {
            const match = field.match(regex);
            const headerName = col.alias?.replace("X", match?.[1]) || field;
            return { field, headerName, minWidth: 120 };
          });
      })
      .flat();
  }, [columnDescriptions, rowsData.rows]);

  // Map codes to fields
  const codeToFieldMap = useMemo(
    () =>
      columnDescriptions.reduce((acc, col) => {
        acc[col.code] = col.name;
        return acc;
      }, {}),
    [columnDescriptions]
  );

  const filteredColumns = useMemo(() => {
    if (!csCodes || csCodes.length === 0) {
      return defaultColumns.filter((col) => {
        const originalCol = columnDescriptions.find(
          (c) => c.name === col.field
        );
        return originalCol?.isDefault;
      });
    }

    const allowedFields = csCodes.flatMap((code) => {
      const template = codeToFieldMap[code];
      if (!template) {
        return [];
      }

      // If no "X" in the template, direct match
      if (!template.includes("X")) {
        return [template];
      }

      // Expand "X" using actual row keys
      const regex = new RegExp("^" + template.replace("X", "(.+)") + "$");
      return rowsData.rows.length > 0
        ? Object.keys(rowsData.rows[0]).filter((k) => regex.test(k))
        : [];
    });

    return defaultColumns.filter((col) => allowedFields.includes(col.field));
  }, [
    csCodes,
    codeToFieldMap,
    defaultColumns,
    columnDescriptions,
    rowsData.rows,
  ]);

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
        rows={rowsData.rows}
        columns={filteredColumns}
        paginationMode="server"
        paginationModel={{ page, pageSize }}
        onPaginationModelChange={handlePaginationModelChange}
        rowCount={rowsData.rowCount}
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
            paddingTop: "8px",
            paddingBottom: "8px",
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
