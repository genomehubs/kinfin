import React, { useEffect, useMemo, useCallback } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useSearchParams } from "react-router-dom";
import { DataGrid } from "@mui/x-data-grid";
import styles from "./AttributeSummary.module.scss";
import { getAttributeSummary } from "../../../app/store/analysis/actions";
import { v4 as uuidv4 } from "uuid";
import { updatePaginationParams } from "@/utilis/urlPagination";

const pageSizeOptions = [10, 25, 50];

const AttributeSummary = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const attributeData = useSelector(
    (state) => state?.analysis?.attributeSummary?.data || null
  );

  // Pull params directly from the URL
  const attribute = searchParams.get("attribute");
  const taxonset = searchParams.get("taxonset");
  const page = Math.max(
    parseInt(searchParams.get("AS_page") || "1", 10) - 1,
    0
  );
  const pageSize = Math.max(
    parseInt(searchParams.get("AS_pageSize") || "10", 10),
    1
  );

  // Only set default pagination if missing from URL
  useEffect(() => {
    const hasPage = searchParams.has("AS_page");
    const hasPageSize = searchParams.has("AS_pageSize");

    if (!hasPage || !hasPageSize) {
      setSearchParams((prev) => {
        const newParams = new URLSearchParams(prev);
        if (!hasPage) newParams.set("AS_page", "1");
        if (!hasPageSize) newParams.set("AS_pageSize", "10");
        return newParams;
      });
    }
  }, [attribute, taxonset, searchParams, setSearchParams]);

  // Fetch data on page, pageSize, attribute changes
  useEffect(() => {
    if (!attribute) return;

    const payload = {
      attribute,
      page: page + 1,
      size: pageSize,
    };

    dispatch(getAttributeSummary(payload));
  }, [attribute, page, pageSize, dispatch]);

  const { rows, rowCount } = useMemo(() => {
    const rawData = attributeData?.data ?? {};
    const processedRows = Object.values(rawData).map((row) => ({
      id: uuidv4(),
      ...row,
      cluster_total_count: row.cluster_total_count ?? "-",
      protein_total_count: row.protein_total_count ?? "-",
      protein_total_span: row.protein_total_span ?? "-",

      singleton_cluster_count: row.singleton?.cluster_count ?? "-",
      singleton_protein_count: row.singleton?.protein_count ?? "-",
      singleton_protein_span: row.singleton?.protein_span ?? "-",

      specific_cluster_count: row.specific?.cluster_count ?? "-",
      specific_protein_count: row.specific?.protein_count ?? "-",
      specific_protein_span: row.specific?.protein_span ?? "-",
      cluster_true_1to1_count: row.specific?.cluster_true_1to1_count ?? "-",
      cluster_fuzzy_count: row.specific?.cluster_fuzzy_count ?? "-",

      shared_cluster_count: row.shared?.cluster_count ?? "-",
      shared_protein_count: row.shared?.protein_count ?? "-",
      shared_protein_span: row.shared?.protein_span ?? "-",
      shared_cluster_true_1to1_count:
        row.shared?.cluster_true_1to1_count ?? "-",
      shared_cluster_fuzzy_count: row.shared?.cluster_fuzzy_count ?? "-",

      absent_cluster_total_count: row.absent?.cluster_total_count ?? "-",
      absent_cluster_singleton_count:
        row.absent?.cluster_singleton_count ?? "-",
      absent_cluster_specific_count: row.absent?.cluster_specific_count ?? "-",
      absent_cluster_shared_count: row.absent?.cluster_shared_count ?? "-",

      TAXON_count: row.TAXON_count ?? "-",
      TAXON_taxa: Array.isArray(row.TAXON_taxa)
        ? row.TAXON_taxa.join(", ")
        : "-",
    }));

    const totalRows =
      attributeData?.total_entries ??
      (attributeData?.total_pages && attributeData?.entries_per_page
        ? attributeData.total_pages * attributeData.entries_per_page
        : processedRows.length);

    return {
      rows: processedRows,
      rowCount: totalRows,
    };
  }, [attributeData]);

  const columns = useMemo(
    () => [
      { field: "taxon_set", headerName: "Taxon Set", minWidth: 150 },

      {
        field: "cluster_total_count",
        headerName: "Total Clusters",
        minWidth: 100,
      },
      {
        field: "protein_total_count",
        headerName: "Total Proteins",
        minWidth: 100,
      },
      {
        field: "protein_total_span",
        headerName: "Protein Span",
        minWidth: 100,
      },

      // Singleton
      {
        field: "singleton_cluster_count",
        headerName: "Singleton Clusters",
        minWidth: 100,
      },
      {
        field: "singleton_protein_count",
        headerName: "Singleton Proteins",
        minWidth: 100,
      },
      {
        field: "singleton_protein_span",
        headerName: "Singleton Protein Span",
        minWidth: 120,
      },

      // Specific
      {
        field: "specific_cluster_count",
        headerName: "Specific Clusters",
        minWidth: 100,
      },
      {
        field: "specific_protein_count",
        headerName: "Specific Proteins",
        minWidth: 100,
      },
      {
        field: "specific_protein_span",
        headerName: "Specific Protein Span",
        minWidth: 120,
      },
      {
        field: "cluster_true_1to1_count",
        headerName: "True 1-to-1 Count",
        minWidth: 130,
      },
      {
        field: "cluster_fuzzy_count",
        headerName: "Fuzzy Count",
        minWidth: 100,
      },

      // Shared
      {
        field: "shared_cluster_count",
        headerName: "Shared Clusters",
        minWidth: 100,
      },
      {
        field: "shared_protein_count",
        headerName: "Shared Proteins",
        minWidth: 100,
      },
      {
        field: "shared_protein_span",
        headerName: "Shared Protein Span",
        minWidth: 120,
      },
      {
        field: "shared_cluster_true_1to1_count",
        headerName: "Shared True 1-to-1 Count",
        minWidth: 160,
      },
      {
        field: "shared_cluster_fuzzy_count",
        headerName: "Shared Fuzzy Count",
        minWidth: 120,
      },

      // Absent
      {
        field: "absent_cluster_total_count",
        headerName: "Absent Clusters",
        minWidth: 100,
      },
      {
        field: "absent_cluster_singleton_count",
        headerName: "Absent Singleton Clusters",
        minWidth: 160,
      },
      {
        field: "absent_cluster_specific_count",
        headerName: "Absent Specific Clusters",
        minWidth: 160,
      },
      {
        field: "absent_cluster_shared_count",
        headerName: "Absent Shared Clusters",
        minWidth: 160,
      },

      { field: "TAXON_count", headerName: "Taxon Count", minWidth: 100 },
      { field: "TAXON_taxa", headerName: "Taxa", minWidth: 150 },
    ],
    []
  );

  const handlePaginationModelChange = useCallback(
    (newModel) => {
      updatePaginationParams(
        searchParams,
        setSearchParams,
        "AS",
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
        rows={rows}
        columns={columns}
        paginationMode="server"
        paginationModel={{ page, pageSize }}
        onPaginationModelChange={handlePaginationModelChange}
        rowCount={rowCount}
        pageSizeOptions={pageSizeOptions}
        disableSelectionOnClick
        checkboxSelection={false}
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

export default AttributeSummary;
