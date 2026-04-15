import React, { useCallback, useMemo } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { DataGrid } from "@mui/x-data-grid";
import { getSessionId } from "#app/utils/session";
import styles from "./ClusterMetrics.module.scss";
import { toCamelCase } from "#utils/changeCase.js";
import { updatePaginationParams } from "@/utils/urlPagination";
import useFullscreen from "#hooks/useFullscreen";
import { useGetClusterMetricsQuery } from "#store/api";
import useIsCurrentPage from "#hooks/useIsCurrentPage";
import usePageCustomisation from "#hooks/usePageCustomisation";
import { v4 as uuidv4 } from "uuid";

const pageSizeOptions = [10, 25, 50];

const ClusterMetrics = ({
  attribute,
  taxonset,
  clusterMetricsColumnDescriptions: columnDescriptions,
}) => {
  const { sessionId: sessionIdFromParams } = useParams();
  const sessionId = sessionIdFromParams || getSessionId();
  const isCurrentPage = useIsCurrentPage("cluster-metrics");
  const { isFullScreen } = useFullscreen();
  const [searchParams, setSearchParams] = useSearchParams();

  const page = Math.max(
    parseInt(searchParams.get("CM_page") || "1", 10) - 1,
    0,
  );
  const pageSize = Math.max(
    parseInt(searchParams.get("CM_pageSize") || "10", 10),
    1,
  );

  const { selectedCodes: cmCodes } = usePageCustomisation({
    searchParamKey: "CM_code",
    columnDescriptions,
  });

  const { data: clusterMetricsResp } = useGetClusterMetricsQuery(
    {
      attribute,
      taxonSet: taxonset,
      sessionId,
      page: page + 1,
      size: pageSize,
      CM_code: cmCodes,
    },
    { skip: !attribute || !taxonset },
  );

  const clusterMetrics = clusterMetricsResp?.data ?? clusterMetricsResp ?? null;

  // fetching handled via RTK Query

  const rowsData = useMemo(() => {
    const raw = clusterMetrics ?? {};
    if (!raw || Object.keys(raw).length === 0) {
      return { rows: [], rowCount: 0 };
    }

    const rows = Object.values(raw).map((row) => ({
      id: row.id || row.clusterId || row.cluster_id || uuidv4(),
      ...Object.fromEntries(
        Object.entries(row).map(([key, value]) => [
          toCamelCase(key),
          value ?? "-",
        ]),
      ),
    }));

    const totalRows =
      clusterMetrics.total_entries ??
      (clusterMetrics.total_pages && clusterMetrics.entries_per_page
        ? clusterMetrics.total_pages * clusterMetrics.entries_per_page
        : rows.length);

    return { rows, rowCount: totalRows };
  }, [clusterMetrics]);

  const defaultColumns = useMemo(() => {
    return columnDescriptions.map((col) => ({
      field: toCamelCase(col.name),
      headerName: col.alias || col.name,
      minWidth: 120,
    }));
  }, [columnDescriptions]);

  // Map codes to fields for cmCodes filtering
  const codeToFieldMap = useMemo(
    () =>
      columnDescriptions.reduce(
        (acc, col) => ({ ...acc, [col.code]: col.name }),
        {},
      ),
    [columnDescriptions],
  );

  const filteredColumns = useMemo(() => {
    if (!cmCodes || cmCodes.length === 0) {
      return defaultColumns.filter((col) => {
        const originalCol = columnDescriptions.find(
          (c) => toCamelCase(c.name) === col.field,
        );
        return originalCol?.isDefault;
      });
    }

    const allowedFields = cmCodes
      .map((code) => toCamelCase(codeToFieldMap[code]))
      .filter(Boolean);

    return defaultColumns.filter((col) => allowedFields.includes(col.field));
  }, [cmCodes, codeToFieldMap, defaultColumns, columnDescriptions]);

  const finalColumns = useMemo(() => {
    const seen = new Set();
    return filteredColumns.filter((col) => {
      if (seen.has(col.field)) return false;
      seen.add(col.field);
      return true;
    });
  }, [filteredColumns]);

  const handlePaginationModelChange = useCallback(
    (newModel) => {
      updatePaginationParams(
        searchParams,
        setSearchParams,
        "CM",
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
        rows={rowsData.rows}
        columns={finalColumns}
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
