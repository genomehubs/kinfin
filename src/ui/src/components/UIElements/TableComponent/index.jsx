import React from "react";
import { useSortBy, useTable } from "react-table";
import styles from "./TableComponent.module.scss";

const TableComponent = ({ columns, data, onRowClick, loading }) => {
  const { getTableProps, getTableBodyProps, headerGroups, rows, prepareRow } =
    useTable(
      {
        columns,
        data,
      },
      useSortBy
    );

  const renderSkeleton = () => {
    const skeletonRows = Array.from({ length: 20 }); // 10 rows
    const skeletonColumns = Array.from({ length: columns.length }); // Match actual column count

    return (
      <tbody className={styles.skeletonBody}>
        {skeletonRows.map((_, rowIndex) => (
          <tr key={`skeleton-row-${rowIndex}`} className={styles.skeletonRow}>
            {skeletonColumns.map((_, colIndex) => (
              <td key={`skeleton-cell-${rowIndex}-${colIndex}`}>
                <div className={styles.skeletonBlock}></div>
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    );
  };

  return (
    <div className={styles.tableParent}>
      <table {...getTableProps()} className={` ${styles.listingTable}`}>
        <thead>
          {headerGroups?.map((headerGroup, i) => (
            <tr {...headerGroup.getHeaderGroupProps()} key={`header-${i}`}>
              {headerGroup.headers.map((column, j) => (
                <th
                  {...column.getHeaderProps(
                    column.sortable ? column.getSortByToggleProps() : {}
                  )}
                  key={`header-${i}-${j}`}
                >
                  {column.render("Header")}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        {loading ? (
          renderSkeleton()
        ) : data?.length ? (
          <tbody className={styles.tableScroll} {...getTableBodyProps()}>
            {rows?.map((row, i) => {
              prepareRow(row);
              return (
                <tr
                  {...row.getRowProps()}
                  onClick={() => onRowClick(row.original)}
                  key={`row-${i}`}
                >
                  {row.cells?.map((cell, j) => (
                    <td {...cell.getCellProps()} key={`cell-${i}-${j}`}>
                      {cell.render("Cell")}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        ) : (
          <tbody className="noData">
            <tr key="no-data">
              <td colSpan={columns?.length}>
                <p style={{ textAlign: "center" }}>No data Found</p>
              </td>
            </tr>
          </tbody>
        )}
      </table>
    </div>
  );
};

export default TableComponent;
