import React, {
  useState,
  useEffect,
  useMemo,
  useRef,
  useCallback,
} from "react";
import { useDispatch, useSelector } from "react-redux";
import { DataGrid } from "@mui/x-data-grid";
import styles from "./AttributeSummary.module.scss";
import { getAttributeSummary } from "../../../app/store/analysis/actions";
import { v4 as uuidv4 } from "uuid";

const pageSizeOptions = [10, 25, 50];

const AttributeSummary = () => {
  const dispatch = useDispatch();
  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: 10,
  });

  const isInitialMount = useRef(true);

  const attributeData = useSelector(
    (state) => state?.analysis?.attributeSummary?.data || null
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
      page: page + 1, // Convert 0-based to 1-based for API
      size: pageSize,
    };

    if (isInitialMount.current) {
      isInitialMount.current = false;
    }

    dispatch(getAttributeSummary(payload));
  }, [paginationModel, selectedAttributeTaxonset?.attribute, dispatch]);

  const { rows, rowCount } = useMemo(() => {
    const rawData = attributeData?.data ?? {};
    const processedRows = Object.values(rawData).map((row, index) => ({
      id: uuidv4(),
      ...row,
      singleton_cluster_count: row?.singleton?.cluster_count ?? "-",
      singleton_protein_count: row?.singleton?.protein_count ?? "-",
      specific_cluster_count: row?.specific?.cluster_count ?? "-",
      shared_cluster_count: row?.shared?.cluster_count ?? "-",
      absent_cluster_total_count: row?.absent?.cluster_total_count ?? "-",
      TAXON_taxa: Array.isArray(row?.TAXON_taxa)
        ? row.TAXON_taxa.join(", ")
        : "-",
    }));

    const totalRows =
      attributeData?.total_entries ??
      (attributeData?.total_pages && attributeData?.entries_per_page
        ? attributeData.total_pages * attributeData.entries_per_page
        : undefined) ??
      processedRows.length;

    return {
      rows: processedRows,
      rowCount: totalRows,
    };
  }, [attributeData, paginationModel.page, paginationModel.pageSize]);

  const columns = useMemo(
    () => [
      { field: "taxon_set", headerName: "Taxon Set", minWidth: 150 },
      {
        field: "cluster_total_count",
        headerName: "Total Clusters",
        minWidth: 80,
      },
      {
        field: "protein_total_count",
        headerName: "Total Proteins",
        minWidth: 80,
      },
      {
        field: "singleton_cluster_count",
        headerName: "Singleton Clusters",
        minWidth: 80,
      },
      {
        field: "singleton_protein_count",
        headerName: "Singleton Proteins",
        minWidth: 80,
      },
      {
        field: "specific_cluster_count",
        headerName: "Specific Clusters",
        minWidth: 80,
      },
      {
        field: "shared_cluster_count",
        headerName: "Shared Clusters",
        minWidth: 80,
      },
      {
        field: "absent_cluster_total_count",
        headerName: "Absent Clusters",
        minWidth: 80,
      },
      {
        field: "TAXON_taxa",
        headerName: "Taxa",
        minWidth: 80,
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
    <div style={{ maxheight: "50vh", width: "100%", overflowX: "auto" }}>
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

export default AttributeSummary;
