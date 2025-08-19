import React, { useEffect, useMemo, useCallback, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useSearchParams } from "react-router-dom";
import { DataGrid } from "@mui/x-data-grid";
import { getAttributeSummary } from "../../../app/store/analysis/slices/attributeSummarySlice";
import { v4 as uuidv4 } from "uuid";
import { updatePaginationParams } from "@/utils/urlPagination";

const pageSizeOptions = [10, 25, 50];

const AttributeSummary = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const attributeData = useSelector(
    (state) => state?.analysis?.attributeSummary?.data || null
  );

  const columnDescriptions = useSelector(
    (state) => state?.config?.columnDescriptions?.data || []
  );

  const attribute = searchParams.get("attribute");

  const asCodes = useMemo(() => searchParams.getAll("AS_code"), [searchParams]);

  const page = Math.max(
    parseInt(searchParams.get("AS_page") || "1", 10) - 1,
    0
  );
  const pageSize = Math.max(
    parseInt(searchParams.get("AS_pageSize") || "10", 10),
    1
  );

  useEffect(() => {
    const hasPage = searchParams.has("AS_page");
    const hasPageSize = searchParams.has("AS_pageSize");

    if (!hasPage || !hasPageSize) {
      const newParams = new URLSearchParams(searchParams);
      if (!hasPage) {
        newParams.set("AS_page", "1");
      }
      if (!hasPageSize) {
        newParams.set("AS_pageSize", "10");
      }
      setSearchParams(newParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    if (!attribute) {
      return;
    }
    const payload = {
      attribute,
      page: page + 1,
      size: pageSize,
      AS_code: asCodes.length > 0 ? asCodes : undefined,
    };
    dispatch(getAttributeSummary(payload));
  }, [attribute, page, pageSize, asCodes, dispatch]);

  const codeToFieldMap = useMemo(() => {
    return columnDescriptions.reduce((acc, col) => {
      acc[col.code] = col.name;
      return acc;
    }, {});
  }, [columnDescriptions]);

  const { rows, rowCount } = useMemo(() => {
    const rawData = attributeData?.data ?? {};
    const processedRows = Object.values(rawData).map((row) => ({
      id: row.id || row.taxon_set || uuidv4(),
      ...Object.fromEntries(
        Object.entries(row).map(([key, value]) => [key, value ?? "-"])
      ),
    }));
    const totalRows =
      attributeData?.total_entries ??
      (attributeData?.total_pages && attributeData?.entries_per_page
        ? attributeData.total_pages * attributeData.entries_per_page
        : processedRows.length);
    return { rows: processedRows, rowCount: totalRows };
  }, [attributeData]);

  const allColumns = useMemo(
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
        field: "specific_cluster_true_1to1_count",
        headerName: "True 1-to-1 Count",
        minWidth: 130,
      },
      {
        field: "specific_cluster_fuzzy_count",
        headerName: "Fuzzy Count",
        minWidth: 100,
      },
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

  const filteredColumns = useMemo(() => {
    if (!asCodes || asCodes.length === 0) {
      return allColumns;
    }
    const allowedFields = asCodes
      .map((code) => codeToFieldMap[code])
      .filter(Boolean);
    return allColumns.filter((col) => allowedFields.includes(col.field));
  }, [asCodes, codeToFieldMap, allColumns]);

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
        columns={filteredColumns}
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
