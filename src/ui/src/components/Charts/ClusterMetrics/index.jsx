import React, { useCallback, useState } from "react";
import ReactPaginate from "react-paginate";
import { useDispatch } from "react-redux";
import TableComponent from "../../UIElements/TableComponent";
import styles from "./ClusterMetrics.module.scss";
import { useSelector } from "react-redux";
import { getClusterMetrics } from "../../../app/store/analysis/actions";

const ClusterMetrics = () => {
  const dispatch = useDispatch();
  const [currentPage, setCurrentPage] = useState(1);
  const handlePageChange = (e) => {
    const newPage = e.selected + 1;
    setCurrentPage(newPage);
    dispatch(
      getClusterMetrics({
        attribute: "host",
        page: newPage,
        taxonSet: "human",
      })
    );
  };

  const data = useSelector(
    (state) => state?.analysis?.clusterMetrics?.data?.data
  );
  const pageCount = useSelector(
    (state) => state?.analysis?.clusterMetrics?.data?.total_pages
  );

  const columns = [
    {
      Header: <span className="tableColHeader">Cluster ID</span>,
      accessor: "cluster_id",
      Cell: ({ value }) => <div>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Cluster Status</span>,
      accessor: "cluster_status",
      Cell: ({ value }) => <div>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Cluster Type</span>,
      accessor: "cluster_type",
      Cell: ({ value }) => <div>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Present in Cluster</span>,
      accessor: "present_in_cluster",
      Cell: ({ value }) => <div>{value ? "Yes" : "No"}</div>,
    },
    {
      Header: <span className="tableColHeader">Singleton</span>,
      accessor: "is_singleton",
      Cell: ({ value }) => <div>{value ? "Yes" : "No"}</div>,
    },
    {
      Header: <span className="tableColHeader">Specific</span>,
      accessor: "is_specific",
      Cell: ({ value }) => <div>{value ? "Yes" : "No"}</div>,
    },
    {
      Header: <span className="tableColHeader">Cluster Protein Count</span>,
      accessor: "counts.cluster_protein_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Cluster Proteome Count</span>,
      accessor: "counts.cluster_proteome_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">TAXON Protein Count</span>,
      accessor: "counts.TAXON_protein_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">TAXON Mean Count</span>,
      accessor: "counts.TAXON_mean_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Non-TAXON Mean Count</span>,
      accessor: "counts.non_taxon_mean_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Representation</span>,
      accessor: "representation",
      Cell: ({ value }) => <div>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Log2 Mean (TAXON/Others)</span>,
      accessor: "log2_mean(TAXON/others)",
      Cell: ({ value }) => <div>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">P-value (TAXON vs Others)</span>,
      accessor: "pvalue(TAXON vs. others)",
      Cell: ({ value }) => <div>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Taxon Coverage</span>,
      accessor: "coverage.taxon_coverage",
      Cell: ({ value }) => <div>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">TAXON Count</span>,
      accessor: "coverage.TAXON_count",
      Cell: ({ value }) => <div>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Non-TAXON Count</span>,
      accessor: "coverage.non_TAXON_count",
      Cell: ({ value }) => <div>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">TAXON Taxa</span>,
      accessor: "TAXON_taxa",
      Cell: useCallback(
        ({ value }) => (
          <div className={styles.Row}>
            {Array.isArray(value) ? value.join(", ") : value ?? "-"}
          </div>
        ),
        []
      ),
    },
    {
      Header: <span className="tableColHeader">Non-TAXON Taxa</span>,
      accessor: "non_TAXON_taxa",
      Cell: useCallback(
        ({ value }) => (
          <div className={styles.Row}>
            {Array.isArray(value) ? value.join(", ") : value ?? "-"}
          </div>
        ),
        []
      ),
    },
  ];

  return (
    <>
      {" "}
      <div className="tableScroll">
        <TableComponent
          columns={columns}
          data={(data && Object.values(data)) ?? []}
          className="listingTable"
          loading={false}
        />
      </div>
      <ReactPaginate
        previousLabel="<"
        nextLabel=">"
        breakLabel={<span className="paginationBreak">...</span>}
        pageCount={pageCount}
        onPageChange={handlePageChange}
        pageRangeDisplayed={4}
        containerClassName={styles.pagination}
        pageClassName="page-item"
        pageLinkClassName="page-link"
        forcePage={currentPage - 1}
      />
    </>
  );
};

export default ClusterMetrics;
