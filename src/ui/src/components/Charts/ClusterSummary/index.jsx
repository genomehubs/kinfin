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
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset || null
  );

  // Parse pagination params from URL or fallback
  const page = Math.max(
    parseInt(searchParams.get("CS_page") || "1", 10) - 1,
    0
  );
  const pageSize = Math.max(
    parseInt(searchParams.get("CS_pageSize") || "5", 10),
    1
  );

  // Set defaults only if not already present in the URL
  useEffect(() => {
    const hasPage = searchParams.has("CS_page");
    const hasPageSize = searchParams.has("CS_pageSize");

    if (!hasPage || !hasPageSize) {
      setSearchParams(
        (prev) => {
          const newParams = new URLSearchParams(prev);
          if (!hasPage) newParams.set("CS_page", "1");
          if (!hasPageSize) newParams.set("CS_pageSize", "5");
          return newParams;
        },
        { replace: true }
      );
    }
  }, [searchParams, setSearchParams]);

  // Fetch cluster summary data
  useEffect(() => {
    const payload = {
      page: page + 1, // Backend is 1-based
      size: pageSize,
      attribute: selectedAttributeTaxonset?.attribute,
    };

    if (payload.attribute) {
      dispatch(getClusterSummary(payload));
    }
  }, [page, pageSize, dispatch, selectedAttributeTaxonset]);

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

  const processedRows = useMemo(() => {
    const rawData = clusterSummaryData?.data ?? {};

    return Object.values(rawData).map((row) => {
      const flatCounts =
        row.protein_counts &&
        Object.entries(row.protein_counts).reduce((acc, [key, value]) => {
          acc[key] = value;
          return acc;
        }, {});

      return {
        id: uuidv4(),
        ...row,
        ...flatCounts,
      };
    });
  }, [clusterSummaryData]);

  const rowCount = useMemo(() => {
    if (clusterSummaryData?.total_entries != null) {
      return clusterSummaryData.total_entries;
    }

    if (
      clusterSummaryData?.total_pages != null &&
      clusterSummaryData?.entries_per_page != null
    ) {
      return (
        clusterSummaryData.total_pages * clusterSummaryData.entries_per_page
      );
    }

    return processedRows.length;
  }, [clusterSummaryData, processedRows]);

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
      minWidth: 80,
    },
    {
      field: "TAXON_count",
      headerName: "TAXON Count",
      minWidth: 80,
    },
    { field: "attribute", headerName: "Attribute", minWidth: 80 },
    {
      field: "attribute_cluster_type",
      headerName: "Cluster Type",
      minWidth: 80,
    },
  ];

  const dynamicColumns = useMemo(() => {
    const firstRow = processedRows[0] || {};
    const dynamicKeys = Object.keys(firstRow).filter(
      (key) =>
        (key.endsWith("_count") ||
          key.endsWith("_median") ||
          key.endsWith("_cov")) &&
        ![
          "cluster_protein_count",
          "TAXON_count",
          "protein_median_count",
        ].includes(key)
    );

    return dynamicKeys.map((key) => ({
      field: key,
      headerName: key
        .replace(/_/g, " ")
        .replace("count", "Count")
        .replace("median", "Median")
        .replace("cov", "Cov")
        .replace(/\b\w/g, (l) => l.toUpperCase()),
      minWidth: 100,
    }));
  }, [processedRows]);

  const columns = useMemo(
    () => [...baseColumns, ...dynamicColumns],
    [dynamicColumns]
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
        rows={processedRows}
        columns={columns}
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

export default ClusterSummary;
