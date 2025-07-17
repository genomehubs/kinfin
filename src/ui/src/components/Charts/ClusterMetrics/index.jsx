import React, {
  useState,
  useEffect,
  useMemo,
  useRef,
  useCallback,
} from "react";
import { useDispatch, useSelector } from "react-redux";
import { DataGrid } from "@mui/x-data-grid";
import styles from "./ClusterMetrics.module.scss";
import { getClusterMetrics } from "../../../app/store/analysis/actions";
import { v4 as uuidv4 } from "uuid";

const pageSizeOptions = [10, 25, 50];

const ClusterMetrics = () => {
  const dispatch = useDispatch();
  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: 10,
  });

  const isInitialMount = useRef(true);

  const clusterMetrics = useSelector(
    (state) => state?.analysis?.clusterMetrics?.data || null
  );
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.selectedAttributeTaxonset || null
  );

  // Reset page to 0 when attribute changes
  useEffect(() => {
    if (selectedAttributeTaxonset?.attribute) {
      setPaginationModel((prev) => ({
        ...prev,
        page: 0,
      }));
    }
  }, [selectedAttributeTaxonset?.attribute]);

  // Fetch attribute summary
  useEffect(() => {
    const { page, pageSize } = paginationModel;

    if (!selectedAttributeTaxonset?.attribute) return;

    const payload = {
      attribute: selectedAttributeTaxonset.attribute,
      taxonSet: selectedAttributeTaxonset.taxonset,
      page: page + 1, // Convert 0-based to 1-based for API
      size: pageSize,
    };

    if (isInitialMount.current) {
      isInitialMount.current = false;
    }

    dispatch(getClusterMetrics(payload));
  }, [paginationModel, selectedAttributeTaxonset?.attribute, dispatch]);

  const { rows, rowCount } = useMemo(() => {
    const rawData = clusterMetrics?.data ?? {};
    const processedRows = Object.values(rawData).map((row, index) => {
      const counts = row?.counts || {};
      const coverage = row?.coverage || {};

      return {
        id: uuidv4(),
        ...row,
        cluster_protein_count: counts.cluster_protein_count ?? "-",
        cluster_proteome_count: counts.cluster_proteome_count ?? "-",
        TAXON_protein_count: counts.TAXON_protein_count ?? "-",
        TAXON_mean_count: counts.TAXON_mean_count ?? "-",
        non_taxon_mean_count: counts.non_taxon_mean_count ?? "-",
        taxon_coverage: coverage.taxon_coverage ?? "-",
        TAXON_count: coverage.TAXON_count ?? "-",
        non_TAXON_count: coverage.non_TAXON_count ?? "-",
        singleton_cluster_count: row?.singleton?.cluster_count ?? "-",
        singleton_protein_count: row?.singleton?.protein_count ?? "-",
        specific_cluster_count: row?.specific?.cluster_count ?? "-",
        shared_cluster_count: row?.shared?.cluster_count ?? "-",
        absent_cluster_total_count: row?.absent?.cluster_total_count ?? "-",
        TAXON_taxa: Array.isArray(row?.TAXON_taxa)
          ? row.TAXON_taxa.join(", ")
          : "-",
      };
    });

    const totalRows =
      clusterMetrics?.total_entries ??
      (clusterMetrics?.total_pages && clusterMetrics?.entries_per_page
        ? clusterMetrics.total_pages * clusterMetrics.entries_per_page
        : undefined) ??
      processedRows.length;

    return {
      rows: processedRows,
      rowCount: totalRows,
    };
  }, [clusterMetrics, paginationModel.page, paginationModel.pageSize]);

  const columns = useMemo(
    () => [
      { field: "cluster_id", headerName: "Cluster ID", minWidth: 120 },
      {
        field: "cluster_status",
        headerName: "Cluster Status",
        minWidth: 120,
      },
      {
        field: "cluster_type",
        headerName: "Cluster Type",
        minWidth: 120,
      },
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
        field: "cluster_protein_count",
        headerName: "Cluster Protein Count",
        minWidth: 120,
      },
      {
        field: "cluster_proteome_count",
        headerName: "Cluster Proteome Count",
        minWidth: 120,
      },
      {
        field: "TAXON_protein_count",
        headerName: "Taxon Protein Count",
        minWidth: 120,
      },
      {
        field: "TAXON_mean_count",
        headerName: "Taxon Mean Count",
        minWidth: 120,
        valueFormatter: (value) => {
          const num = Number(value);
          return isNaN(num) ? "-" : num.toFixed(2);
        },
      },
      {
        field: "non_taxon_mean_count",
        headerName: "Non-Taxon Mean Count",
        minWidth: 120,
        valueFormatter: (value) => {
          const num = Number(value);
          return isNaN(num) ? "-" : num.toFixed(2);
        },
      },
      {
        field: "representation",
        headerName: "Representation",
        minWidth: 120,
      },
      {
        field: "log2_mean(TAXON/others)",
        headerName: "Log2 Mean ",
        minWidth: 120,
        valueFormatter: (value) => {
          const num = Number(value);
          return isNaN(num) ? "-" : num.toFixed(2);
        },
      },
      {
        field: "pvalue(TAXON vs. others)",
        headerName: "P-value",
        minWidth: 120,
        valueFormatter: (value) => {
          const num = Number(value);
          return isNaN(num) ? "-" : num.toFixed(2);
        },
      },
      {
        field: "taxon_coverage",
        headerName: "Taxon Coverage",
        minWidth: 120,
      },
      {
        field: "TAXON_count",
        headerName: "TAXON Count",
        minWidth: 120,
      },
      {
        field: "non_TAXON_count",
        headerName: "Non-Taxon Count",
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

  const handlePaginationModelChange = useCallback(
    (newPaginationModel) => {
      if (
        newPaginationModel.page !== paginationModel.page ||
        newPaginationModel.pageSize !== paginationModel.pageSize
      ) {
        setPaginationModel(newPaginationModel);
      }
    },
    [paginationModel]
  );

  return (
    <div style={{ height: "50vh", width: "100%", overflowX: "auto" }}>
      <DataGrid
        rows={rows}
        columns={columns}
        paginationMode="server"
        paginationModel={paginationModel}
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
        }}
      />
    </div>
  );
};

export default ClusterMetrics;
