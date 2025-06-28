import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useSelector, useDispatch } from "react-redux";
import { DataGrid } from "@mui/x-data-grid";
import styles from "./ClusterSummary.module.scss";
import { getClusterSummary } from "../../../app/store/analysis/actions";

const pageSizeOptions = [5, 10, 25];

const ClusterSummary = () => {
  const dispatch = useDispatch();

  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: 5,
  });

  const clusterSummaryData = useSelector(
    (state) => state?.analysis?.clusterSummary?.data
  );
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.selectedAttributeTaxonset || null
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

  useEffect(() => {
    const { page, pageSize } = paginationModel;

    const payload = {
      page: page + 1, // Backend is 1-based
      size: pageSize,
      attribute: selectedAttributeTaxonset?.attribute,
    };

    if (payload.attribute) {
      dispatch(getClusterSummary(payload));
    }
  }, [paginationModel, dispatch, selectedAttributeTaxonset]);

  const processedRows = useMemo(() => {
    const rawData = clusterSummaryData?.data ?? {};

    return Object.values(rawData).map((row) => {
      const flatCounts =
        row.protein_counts &&
        Object.entries(row.protein_counts).reduce((acc, [key, value]) => {
          acc[key] = value;
          return acc;
        }, {});

      return {
        id: row.cluster_id,
        ...row,
        ...flatCounts,
      };
    });
  }, [clusterSummaryData]);

  const rowCount = useMemo(() => {
    return (
      clusterSummaryData?.total_entries ??
      clusterSummaryData?.total_pages * clusterSummaryData?.entries_per_page ??
      processedRows.length
    );
  }, [clusterSummaryData, processedRows]);

  const baseColumns = [
    { field: "cluster_id", headerName: "Cluster ID", flex: 1 },
    { field: "cluster_protein_count", headerName: "Total Proteins", flex: 1 },
    { field: "protein_median_count", headerName: "Median Count", flex: 1 },
    { field: "TAXON_count", headerName: "TAXON Count", flex: 1 },
    { field: "attribute", headerName: "Attribute", flex: 1 },
    { field: "attribute_cluster_type", headerName: "Cluster Type", flex: 1 },
  ];

  const dynamicColumns = useMemo(() => {
    const firstRow = processedRows[0] || {};
    const dynamicKeys = Object.keys(firstRow).filter(
      (key) =>
        key.endsWith("_count") &&
        !["cluster_protein_count", "TAXON_count"].includes(key)
    );

    return dynamicKeys.map((key) => ({
      field: key,
      headerName: key.replace(/_/g, " ").replace("count", "Count"),
      flex: 1,
    }));
  }, [processedRows]);

  const columns = useMemo(
    () => [...baseColumns, ...dynamicColumns],
    [dynamicColumns]
  );

  return (
    <div className={styles.container}>
      <DataGrid
        rows={processedRows}
        columns={columns}
        paginationMode="server"
        paginationModel={paginationModel}
        onPaginationModelChange={handlePaginationModelChange}
        rowCount={rowCount}
        pageSizeOptions={pageSizeOptions}
        disableSelectionOnClick
        checkboxSelection={false}
        autoHeight
        className={styles.listingTable}
      />
    </div>
  );
};

export default ClusterSummary;
