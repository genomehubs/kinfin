import React, { useCallback, useState } from "react";
import ReactPaginate from "react-paginate";
import { useDispatch } from "react-redux";
import TableComponent from "../../UIElements/TableComponent";
import styles from "./AttributeSummary.module.scss";
import { useSelector } from "react-redux";
import { getAttributeSummary } from "../../../app/store/kinfin/actions";

const AttributeSummary = () => {
  const dispatch = useDispatch();
  const [currentPage, setCurrentPage] = useState(1);
  const handlePageChange = (e) => {
    const newPage = e.selected + 1;
    setCurrentPage(newPage);
    dispatch(getAttributeSummary({ attribute: "host", page: newPage }));
  };

  const data = useSelector(
    (state) => state?.analysis?.attributeSummary?.data?.data
  );
  const pageCount = useSelector(
    (state) => state?.analysis?.attributeSummary?.data?.total_pages
  );

  const columns = [
    {
      Header: <span className="tableColHeader">Taxon Set</span>,
      accessor: "taxon_set",
      Cell: ({ value }) => <div>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Total Clusters</span>,
      accessor: "cluster_total_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Total Proteins</span>,
      accessor: "protein_total_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Singleton Clusters</span>,
      accessor: "singleton.cluster_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Singleton Proteins</span>,
      accessor: "singleton.protein_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Specific Clusters</span>,
      accessor: "specific.cluster_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Shared Clusters</span>,
      accessor: "shared.cluster_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Absent Clusters</span>,
      accessor: "absent.cluster_total_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Taxon Count</span>,
      accessor: "TAXON_count",
      Cell: ({ value }) => <div className={styles.Row}>{value ?? "-"}</div>,
    },
    {
      Header: <span className="tableColHeader">Taxa</span>,
      accessor: "TAXON_taxa",
      Cell: useCallback(
        ({ value }) => (
          <div className={styles.Row}>{value?.join(", ") ?? "-"}</div>
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

export default AttributeSummary;
