import React, { useState } from "react";
import ReactPaginate from "react-paginate";
import { useDispatch } from "react-redux";
import TableComponent from "../../UIElements/TableComponent";
import styles from "./ClusterSummary.module.scss";
import { useSelector } from "react-redux";
import * as AnalysisActions from "../../../app/store/kinfin/actions";

const ClusterSummary = () => {
  const dispatch = useDispatch();
  const [currentPage, setCurrentPage] = useState(1);
  const handlePageChange = (e) => {
    const newPage = e.selected + 1;
    setCurrentPage(newPage); // Update state
    dispatch(
      AnalysisActions.getClusterSummary({ attribute: "host", page: newPage })
    );
  };

  const data = useSelector(
    (state) => state?.analysis?.clusterSummary?.data?.data
  );
  const pageCount = useSelector(
    (state) => state?.analysis?.clusterSummary?.data?.total_pages
  );

  const columns = [
    {
      Header: <span className="tableColHeader">Cluster ID</span>,
      accessor: "cluster_id",
      Cell: ({ value }) => <div>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Cluster Protein Count</span>,
      accessor: "cluster_protein_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Protein Median Count</span>,
      accessor: "protein_median_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">TAXON Count</span>,
      accessor: "TAXON_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Attribute</span>,
      accessor: "attribute",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Cluster Type</span>,
      accessor: "attribute_cluster_type",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Human Count</span>,
      accessor: "protein_counts.human_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Other Count</span>,
      accessor: "protein_counts.other_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Outgroup Count</span>,
      accessor: "protein_counts.outgroup_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Human Median</span>,
      accessor: "protein_counts.human_median",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Other Median</span>,
      accessor: "protein_counts.other_median",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Outgroup Median</span>,
      accessor: "protein_counts.outgroup_median",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Human Coverage</span>,
      accessor: "protein_counts.human_cov",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Other Coverage</span>,
      accessor: "protein_counts.other_cov",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Outgroup Coverage</span>,
      accessor: "protein_counts.outgroup_cov",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
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

export default ClusterSummary;
