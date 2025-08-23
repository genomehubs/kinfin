import React, { useEffect, useMemo, useCallback } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useSearchParams } from "react-router-dom";
import { DataGrid } from "@mui/x-data-grid";
import styles from "./ClusterMetrics.module.scss";
import { getClusterMetrics } from "../../../app/store/analysis/slices/clusterMetricsSlice";
import { v4 as uuidv4 } from "uuid";
import { updatePaginationParams } from "@/utils/urlPagination";

const pageSizeOptions = [10, 25, 50];

const ClusterMetrics = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const clusterMetrics = useSelector(
    (state) => state?.analysis?.clusterMetrics?.data || null
  );
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset || null
  );

  const columnDescriptions = useSelector((state) =>
    (state?.config?.columnDescriptions?.data || []).filter(
      (col) => col.file === "*.cluster_metrics.txt"
    )
  );

  const attribute = selectedAttributeTaxonset?.attribute || null;
  const taxonSet = selectedAttributeTaxonset?.taxonset || null;

  const page = Math.max(
    parseInt(searchParams.get("CM_page") || "1", 10) - 1,
    0
  );
  const pageSize = Math.max(
    parseInt(searchParams.get("CM_pageSize") || "10", 10),
    1
  );

  // Apply default pagination params if missing
  useEffect(() => {
    const newParams = new URLSearchParams(searchParams);
    if (!searchParams.has("CM_page")) {
      newParams.set("CM_page", "1");
    }
    if (!searchParams.has("CM_pageSize")) {
      newParams.set("CM_pageSize", "10");
    }
    setSearchParams(newParams, { replace: true });
  }, [searchParams, setSearchParams]);

  // cmCodes from URL
  const cmCodes = useMemo(() => searchParams.getAll("CM_code"), [searchParams]);
  // Fetch cluster metrics
  useEffect(() => {
    if (!attribute || !taxonSet) {
      return;
    }

    dispatch(
      getClusterMetrics({
        attribute,
        taxonSet,
        page: page + 1,
        size: pageSize,
        CM_code: cmCodes,
      })
    );
  }, [dispatch, attribute, taxonSet, page, pageSize, cmCodes]);

  const rowsData = useMemo(() => {
    if (!clusterMetrics?.data) {
      return { rows: [], rowCount: 0 };
    }

    const rows = Object.values(clusterMetrics.data).map((row) => ({
      id: uuidv4(),
      ...row,
    }));

    const totalRows =
      clusterMetrics.total_entries ??
      (clusterMetrics.total_pages && clusterMetrics.entries_per_page
        ? clusterMetrics.total_pages * clusterMetrics.entries_per_page
        : rows.length);

    return { rows, rowCount: totalRows };
  }, [clusterMetrics]);

  const defaultColumns = useMemo(() => {
    return columnDescriptions.map((col) => ({
      field: col.name,
      headerName: col.alias || col.name,
      minWidth: 120,
    }));
  }, [columnDescriptions]);

  // Map codes to fields for cmCodes filtering
  const codeToFieldMap = useMemo(
    () =>
      columnDescriptions.reduce(
        (acc, col) => ({ ...acc, [col.code]: col.name }),
        {}
      ),
    [columnDescriptions]
  );

  const filteredColumns = useMemo(() => {
    if (!cmCodes || cmCodes.length === 0) {
      return defaultColumns.filter((col) => {
        const originalCol = columnDescriptions.find(
          (c) => c.name === col.field
        );
        return originalCol?.isDefault;
      });
    }

    const allowedFields = cmCodes
      .map((code) => codeToFieldMap[code])
      .filter(Boolean);

    return defaultColumns.filter((col) => allowedFields.includes(col.field));
  }, [cmCodes, codeToFieldMap, defaultColumns, columnDescriptions]);

  const handlePaginationModelChange = useCallback(
    (newModel) => {
      updatePaginationParams(
        searchParams,
        setSearchParams,
        "CM",
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
            borderBottom: "1px solid  #cccccc",
            borderTop: "1px solid  #cccccc",
          },
          "& .MuiDataGrid-row:nth-of-type(odd)": {
            backgroundColor: "#ffffff",
          },
          "& .MuiDataGrid-row:nth-of-type(even)": {
            backgroundColor: "#fafafa",
          },
        }}
      />
    </div>
  );
};

export default ClusterMetrics;
