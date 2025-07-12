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
        id: index + paginationModel.page * paginationModel.pageSize,
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
      clusterMetrics?.total_pages * clusterMetrics?.entries_per_page ??
      processedRows.length;

    return {
      rows: processedRows,
      rowCount: totalRows,
    };
  }, [clusterMetrics, paginationModel.page, paginationModel.pageSize]);

  const columns = useMemo(
    () => [
      { field: "cluster_id", headerName: "Cluster ID", flex: 1 },
      { field: "cluster_status", headerName: "Cluster Status", flex: 1 },
      { field: "cluster_type", headerName: "Cluster Type", flex: 1 },
      {
        field: "present_in_cluster",
        headerName: "Present in Cluster",
        flex: 1,
        valueFormatter: ({ value }) => (value ? "Yes" : "No"),
      },
      {
        field: "is_singleton",
        headerName: "Singleton",
        flex: 1,
        valueFormatter: ({ value }) => (value ? "Yes" : "No"),
      },
      {
        field: "is_specific",
        headerName: "Specific",
        flex: 1,
        valueFormatter: ({ value }) => (value ? "Yes" : "No"),
      },
      {
        field: "cluster_protein_count",
        headerName: "Cluster Protein Count",
        flex: 1,
      },
      {
        field: "cluster_proteome_count",
        headerName: "Cluster Proteome Count",
        flex: 1,
      },
      {
        field: "TAXON_protein_count",
        headerName: "TAXON Protein Count",
        flex: 1,
      },
      {
        field: "TAXON_mean_count",
        headerName: "TAXON Mean Count",
        flex: 1,
      },
      {
        field: "non_taxon_mean_count",
        headerName: "Non-TAXON Mean Count",
        flex: 1,
      },
      {
        field: "representation",
        headerName: "Representation",
        flex: 1,
      },
      {
        field: "log2_mean(TAXON/others)",
        headerName: "Log2 Mean (TAXON/Others)",
        flex: 1,
      },
      {
        field: "pvalue(TAXON vs. others)",
        headerName: "P-value (TAXON vs Others)",
        flex: 1,
      },
      {
        field: "taxon_coverage",
        headerName: "Taxon Coverage",
        flex: 1,
      },
      {
        field: "TAXON_count",
        headerName: "TAXON Count",
        flex: 1,
      },
      {
        field: "non_TAXON_count",
        headerName: "Non-TAXON Count",
        flex: 1,
      },
      {
        field: "TAXON_taxa",
        headerName: "TAXON Taxa",
        flex: 1,
        renderCell: ({ value }) =>
          Array.isArray(value) ? value.join(", ") : value ?? "-",
      },
      {
        field: "non_TAXON_taxa",
        headerName: "Non-TAXON Taxa",
        flex: 1,
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
    <div style={{ height: "70vh", width: "100%" }}>
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
          "& .MuiDataGrid-columnHeader": {
            whiteSpace: "normal",
            lineHeight: "normal",
          },
          "& .MuiDataGrid-columnHeaderTitle": {
            fontWeight: "bold",
            whiteSpace: "normal",
            lineHeight: "normal",
          },
        }}
      />
    </div>
  );
};

export default ClusterMetrics;
