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
      setSearchParams(
        (prev) => {
          const newParams = new URLSearchParams(prev);
          if (!hasPage) newParams.set("AS_page", "1");
          if (!hasPageSize) newParams.set("AS_pageSize", "10");
          return newParams;
        },
        { replace: true }
      );
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
      { field: "TAXON_taxa", headerName: "Taxa", minWidth: 80 },
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
