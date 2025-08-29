import React, { useCallback, useEffect, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";

import { DataGrid } from "@mui/x-data-grid";
import { getAttributeSummary } from "../../../app/store/analysis/slices/attributeSummarySlice";
import { updatePaginationParams } from "@/utils/urlPagination";
import { useSearchParams } from "react-router-dom";
import { v4 as uuidv4 } from "uuid";

const pageSizeOptions = [10, 25, 50];

const AttributeSummary = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const attributeData = useSelector(
    (state) => state?.analysis?.attributeSummary?.data || null
  );

  const columnDescriptions = useSelector((state) =>
    (state?.config?.columnDescriptions?.data || []).filter(
      (col) => col.file === "*.attribute_metrics.txt"
    )
  );

  const attribute = searchParams.get("attribute");

  const asCodes = useMemo(() => {
    if (!searchParams.has("AS_code")) {
      return columnDescriptions
        .filter((col) => col.isDefault)
        .map((col) => col.code);
    }
    return searchParams.getAll("AS_code");
  }, [searchParams, columnDescriptions]);

  const page = Math.max(
    parseInt(searchParams.get("AS_page") || "1", 10) - 1,
    0
  );
  const pageSize = Math.max(
    parseInt(searchParams.get("AS_pageSize") || "10", 10),
    1
  );

  // Fetch attribute summary
  useEffect(() => {
    if (!attribute) {
      return;
    }

    dispatch(
      getAttributeSummary({
        attribute,
        page: page + 1,
        size: pageSize,
        AS_code: asCodes.length > 0 ? asCodes : undefined,
      })
    );
  }, [attribute, page, pageSize, asCodes, dispatch]);

  // Map codes to field names
  const codeToFieldMap = useMemo(
    () =>
      columnDescriptions.reduce((acc, col) => {
        acc[col.code] = col.name;
        return acc;
      }, {}),
    [columnDescriptions]
  );

  // Prepare rows
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

  // Columns loaded dynamically
  const defaultColumns = useMemo(() => {
    return columnDescriptions.map((col) => ({
      field: col.name,
      headerName: col.alias || col.name,
      minWidth: 120,
    }));
  }, [columnDescriptions]);

  const filteredColumns = useMemo(() => {
    if (!asCodes || asCodes.length === 0) {
      return defaultColumns.filter((col) => {
        const originalCol = columnDescriptions.find(
          (c) => c.name === col.field
        );
        return originalCol?.isDefault;
      });
    }

    const allowedFields = asCodes
      .map((code) => codeToFieldMap[code])
      .filter(Boolean);

    return defaultColumns.filter((col) => allowedFields.includes(col.field));
  }, [asCodes, codeToFieldMap, defaultColumns, columnDescriptions]);

  // Pagination handler
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
          "& .MuiDataGrid-row:nth-of-type(odd)": { backgroundColor: "#ffffff" },
          "& .MuiDataGrid-row:nth-of-type(even)": {
            backgroundColor: "#fafafa",
          },
        }}
      />
    </div>
  );
};

export default AttributeSummary;
