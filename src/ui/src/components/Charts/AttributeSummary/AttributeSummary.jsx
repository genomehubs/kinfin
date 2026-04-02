import React, { useCallback, useMemo } from "react";

import { DataGrid } from "@mui/x-data-grid";
import { toCamelCase } from "#utils/changeCase.js";
import { updatePaginationParams } from "@/utils/urlPagination";
import useFullscreen from "#hooks/useFullscreen";
import { useGetAttributeSummaryQuery } from "#store/api";
import useIsCurrentPage from "#hooks/useIsCurrentPage";
import usePageCustomisation from "#hooks/usePageCustomisation";
import { useSearchParams } from "react-router-dom";
import { v4 as uuidv4 } from "uuid";

const pageSizeOptions = [10, 25, 50];

const AttributeSummary = ({
  attribute,
  attributeSummaryColumnDescriptions: columnDescriptions,
}) => {
  const isCurrentPage = useIsCurrentPage("attribute-summary");
  const { isFullScreen } = useFullscreen();

  const [searchParams, setSearchParams] = useSearchParams();

  // Use RTK Query to fetch attribute summary for current session/attribute
  const page = Math.max(
    parseInt(searchParams.get("AS_page") || "1", 10) - 1,
    0,
  );
  const pageSize = Math.max(
    parseInt(searchParams.get("AS_pageSize") || "10", 10),
    1,
  );

  const { selectedCodes: asCodes, setSelectedCodes: setAsCodes } =
    usePageCustomisation({
      searchParamKey: "AS_code",
      columnDescriptions,
    });

  // Fetching is handled by RTK Query hook above

  const { data: attributeResp } = useGetAttributeSummaryQuery(
    {
      attribute,
      page: page + 1,
      size: pageSize,
      AS_code: asCodes.length > 0 ? asCodes : undefined,
    },
    { skip: !attribute },
  );

  const attributeData = attributeResp?.data ?? attributeResp ?? null;
  // Map codes to field names
  const codeToFieldMap = useMemo(
    () =>
      columnDescriptions.reduce((acc, col) => {
        acc[col.code] = col.name;
        return acc;
      }, {}),
    [columnDescriptions],
  );

  // Prepare rows
  const { rows, rowCount } = useMemo(() => {
    const rawData = attributeData ?? {};
    const processedRows = Object.values(rawData).map((row) => ({
      id: row.id || row.taxonSet || row.taxon_set || uuidv4(),
      ...Object.fromEntries(
        Object.entries(row).map(([key, value]) => [
          toCamelCase(key),
          value ?? "-",
        ]),
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
      field: toCamelCase(col.name),
      headerName: col.alias || col.name,
      minWidth: 120,
    }));
  }, [columnDescriptions]);

  const filteredColumns = useMemo(() => {
    if (!asCodes || asCodes.length === 0) {
      return defaultColumns.filter((col) => {
        const originalCol = columnDescriptions.find(
          (c) => toCamelCase(c.name) === col.field,
        );
        return originalCol?.isDefault;
      });
    }

    const allowedFields = asCodes
      .map((code) => toCamelCase(codeToFieldMap[code]))
      .filter(Boolean);

    return defaultColumns.filter((col) => allowedFields.includes(col.field));
  }, [asCodes, codeToFieldMap, defaultColumns, columnDescriptions]);

  const finalColumns = useMemo(() => {
    const seen = new Set();
    return filteredColumns.filter((col) => {
      if (seen.has(col.field)) return false;
      seen.add(col.field);
      return true;
    });
  }, [filteredColumns]);
  // Pagination handler
  const handlePaginationModelChange = useCallback(
    (newModel) => {
      updatePaginationParams(
        searchParams,
        setSearchParams,
        "AS",
        newModel.page,
        newModel.pageSize,
      );
    },
    [searchParams, setSearchParams],
  );

  return (
    <div
      style={{
        maxHeight: isCurrentPage
          ? isFullScreen
            ? "100vh"
            : "calc(100vh - 200px)"
          : "50vh",
        width: "100%",
        overflowX: "auto",
        borderRadius: "12px",
      }}
    >
      <DataGrid
        rows={rows}
        columns={finalColumns}
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
