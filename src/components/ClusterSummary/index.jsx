import React, { useState } from "react";
import styles from "./ClusterSummary.module.scss";
import { FaChevronDown, FaChevronUp } from "react-icons/fa";
import { useSelector } from "react-redux";

const ClusterSummary = () => {
  const [expandedRow, setExpandedRow] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 5;

  const toggleRow = (id) => {
    setExpandedRow(expandedRow === id ? null : id);
  };

  const clusterSummaryData = useSelector(
    (state) => state?.analysis?.clusterSummary?.data
  );

  const data = clusterSummaryData ? Object.values(clusterSummaryData) : [];

  const paginatedData = data.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  return (
    <div className={styles.container}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Cluster ID</th>
            <th>Total Proteins</th>
            <th>Median Count</th>
            <th>TAXON Count</th>
            <th>Attribute</th>
            <th>Cluster Type</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {paginatedData.map((cluster) => (
            <React.Fragment key={cluster.cluster_id}>
              <tr>
                <td>{cluster.cluster_id}</td>
                <td>{cluster.cluster_protein_count}</td>
                <td>{cluster.protein_median_count}</td>
                <td>{cluster.TAXON_count}</td>
                <td>{cluster.attribute}</td>
                <td>{cluster.attribute_cluster_type}</td>
                <td>
                  <button onClick={() => toggleRow(cluster.cluster_id)}>
                    {expandedRow === cluster.cluster_id ? (
                      <FaChevronUp />
                    ) : (
                      <FaChevronDown />
                    )}
                  </button>
                </td>
              </tr>
              {expandedRow === cluster.cluster_id && (
                <tr className={styles.expandedRow}>
                  <td colSpan="7">
                    <div className={styles.details}>
                      <p>
                        <strong>Human Count:</strong>{" "}
                        {cluster.protein_counts?.human_count || "N/A"}
                      </p>
                      <p>
                        <strong>Other Count:</strong>{" "}
                        {cluster.protein_counts?.other_count || "N/A"}
                      </p>
                      <p>
                        <strong>Outgroup Count:</strong>{" "}
                        {cluster.protein_counts?.outgroup_count || "N/A"}
                      </p>
                    </div>
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
      <div className={styles.pagination}>
        <button
          onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
          disabled={currentPage === 1}
        >
          Previous
        </button>
        <span>Page {currentPage}</span>
        <button
          onClick={() =>
            setCurrentPage((prev) =>
              prev * rowsPerPage >= data.length ? prev : prev + 1
            )
          }
          disabled={currentPage * rowsPerPage >= data.length}
        >
          Next
        </button>
      </div>
    </div>
  );
};

export default ClusterSummary;
