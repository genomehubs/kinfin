import React, { useEffect, useMemo, useCallback, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useSearchParams } from "react-router-dom";
import { DataGrid } from "@mui/x-data-grid";
import styles from "./ClusterMetrics.module.scss";
import { v4 as uuidv4 } from "uuid";
import { getClusterMetrics } from "../../../app/store/analysis/actions";
import { updatePaginationParams } from "@/utilis/urlPagination";

const pageSizeOptions = [10, 25, 50];

const ClusterMetrics = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const clusterMetrics = useSelector(
    (state) => state?.analysis?.clusterMetrics?.data || null
  );
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.selectedAttributeTaxonset || null
  );
  const columnDescriptions = useSelector(
    (state) => state?.config?.columnDescriptions?.data || []
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
    const hasPage = searchParams.has("CM_page");
    const hasPageSize = searchParams.has("CM_pageSize");

    if (!hasPage || !hasPageSize) {
      const newParams = new URLSearchParams(searchParams);
      if (!hasPage) {
        newParams.set("CM_page", "1");
      }
      if (!hasPageSize) {
        newParams.set("CM_pageSize", "10");
      }
      setSearchParams(newParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  // Dynamic column filtering
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

    const processed = Object.values(clusterMetrics.data).map((row) => ({
      id: uuidv4(),
      ...row,
      counts_cluster_protein_count: row.counts_cluster_protein_count ?? "-",
      counts_cluster_proteome_count: row.counts_cluster_proteome_count ?? "-",
      counts_TAXON_protein_count: row.counts_TAXON_protein_count ?? "-",
      counts_TAXON_mean_count: row.counts_TAXON_mean_count ?? "-",
      counts_non_taxon_mean_count: row.counts_non_taxon_mean_count ?? "-",
      coverage_TAXON_coverage: row.coverage_taxon_coverage ?? "-",
      representation: row.representation ?? "-",
      "log2_mean(TAXON/others)": row["log2_mean(TAXON/others)"] ?? "-",
      "pvalue(TAXON vs. others)": row["pvalue(TAXON vs. others)"] ?? "-",
      coverage_TAXON_count: row.coverage_TAXON_count ?? "-",
      coverage_non_TAXON_count: row.coverage_non_TAXON_count ?? "-",
      singleton_cluster_count: row.is_singleton ? 1 : 0,
      singleton_protein_count: row.is_singleton
        ? row.counts_cluster_protein_count
        : 0,
      specific_cluster_count: row.is_specific ? 1 : 0,
      shared_cluster_count: row.cluster_type === "shared" ? 1 : 0,
      absent_cluster_total_count: row.cluster_status === "absent" ? 1 : 0,
      TAXON_taxa: row.TAXON_taxa ? row.TAXON_taxa.split(",") : [],
      non_TAXON_taxa: row.non_TAXON_taxa ? row.non_TAXON_taxa.split(",") : [],
    }));

    const totalRows =
      clusterMetrics.total_entries ??
      (clusterMetrics.total_pages && clusterMetrics.entries_per_page
        ? clusterMetrics.total_pages * clusterMetrics.entries_per_page
        : processed.length);

    return { rows: processed, rowCount: totalRows };
  }, [clusterMetrics]);

  // Default columns
  const defaultColumns = useMemo(
    () => [
      { field: "cluster_id", headerName: "Cluster ID", minWidth: 120 },
      { field: "cluster_status", headerName: "Cluster Status", minWidth: 120 },
      { field: "cluster_type", headerName: "Cluster Type", minWidth: 120 },
      {
        field: "present_in_cluster",
        headerName: "Present in Cluster",
        minWidth: 120,
        valueFormatter: ({ value }) => (value ? "Yes" : "No"),
      },
      {
        field: "is_singleton",
        headerName: "Singleton",
        minWidth: 120,
        valueFormatter: ({ value }) => (value ? "Yes" : "No"),
      },
      {
        field: "is_specific",
        headerName: "Specific",
        minWidth: 120,
        valueFormatter: ({ value }) => (value ? "Yes" : "No"),
      },
      {
        field: "counts_cluster_protein_count",
        headerName: "Cluster Protein Count",
        minWidth: 120,
      },
      {
        field: "counts_cluster_proteome_count",
        headerName: "Cluster Proteome Count",
        minWidth: 120,
      },
      {
        field: "counts_TAXON_protein_count",
        headerName: "Taxon Protein Count",
        minWidth: 120,
      },
      {
        field: "representation",
        headerName: "Representation",
        minWidth: 120,
      },
      {
        field: "log2_mean(TAXON/others)",
        headerName: "log2 mean(TAXON/others)",
        minWidth: 120,
      },
      {
        field: "pvalue(TAXON vs. others)",
        headerName: "pvalue(TAXON vs. others)",
        minWidth: 120,
      },
      {
        field: "counts_TAXON_mean_count",
        headerName: "Taxon Mean Count",
        minWidth: 120,
        valueFormatter: (value) =>
          isNaN(Number(value)) ? "-" : Number(value).toFixed(2),
      },
      {
        field: "counts_non_taxon_mean_count",
        headerName: "Non-Taxon Mean Count",
        minWidth: 120,
        valueFormatter: (value) =>
          isNaN(Number(value)) ? "-" : Number(value).toFixed(2),
      },
      {
        field: "coverage_TAXON_coverage",
        headerName: "Taxon Coverage",
        minWidth: 120,
      },
      {
        field: "coverage_TAXON_count",
        headerName: "TAXON Count",
        minWidth: 120,
      },
      {
        field: "coverage_non_TAXON_count",
        headerName: "Non-TAXON Count",
        minWidth: 120,
      },
      {
        field: "TAXON_taxa",
        headerName: "TAXON Taxa",
        minWidth: 120,
        renderCell: ({ value }) =>
          Array.isArray(value) ? value.join(", ") : value ?? "-",
      },
      {
        field: "non_TAXON_taxa",
        headerName: "Non-TAXON Taxa",
        minWidth: 120,
        renderCell: ({ value }) =>
          Array.isArray(value) ? value.join(", ") : value ?? "-",
      },
    ],
    []
  );

  const codeToFieldMap = useMemo(() => {
    return columnDescriptions.reduce((acc, col) => {
      acc[col.code] = col.name;
      return acc;
    }, {});
  }, [columnDescriptions]);

  const filteredColumns = useMemo(() => {
    if (!cmCodes || cmCodes.length === 0) {
      return defaultColumns;
    }
    const allowedFields = cmCodes
      .map((code) => codeToFieldMap[code])
      .filter(Boolean);
    return defaultColumns.filter((col) => allowedFields.includes(col.field));
  }, [cmCodes, codeToFieldMap, defaultColumns]);

  // Handle pagination
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
