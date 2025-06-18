import React from "react";
import styles from "./DataTable.module.scss";

const DataTable = ({
  parsedData,
  validationErrors = { headers: [], rows: [] },
  handleHeaderEdit = () => {},
  handleCellEdit = () => {},
  allowEdit = true, // default true
}) => {
  if (!Array.isArray(parsedData)) return <p>Data is not in tabular format.</p>;
  if (parsedData.length === 0) return <p>No data to display.</p>;

  const headers = Object.keys(parsedData[0]);

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          {headers.map((head) => {
            const hasHeaderError = allowEdit
              ? validationErrors.headers.some((err) => err.includes(head))
              : false;

            const headerErrorMsg = allowEdit
              ? validationErrors.headers.find((err) =>
                  err.toLowerCase().includes(`'${head.trim().toLowerCase()}'`)
                )
              : "";

            return (
              <th
                key={head}
                className={hasHeaderError ? styles.invalidHeader : ""}
                title={hasHeaderError ? headerErrorMsg : ""}
              >
                {allowEdit ? (
                  <div
                    contentEditable
                    suppressContentEditableWarning
                    onBlur={(e) => {
                      const newHeader = e.target.textContent.trim();
                      if (newHeader && newHeader !== head) {
                        handleHeaderEdit(head, newHeader);
                      }
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        e.target.blur();
                      }
                    }}
                    style={{ minWidth: "100px", padding: "4px" }}
                  >
                    {head}
                  </div>
                ) : (
                  <div style={{ minWidth: "100px", padding: "4px" }}>
                    {head}
                  </div>
                )}
              </th>
            );
          })}
        </tr>
      </thead>
      <tbody>
        {parsedData.map((row, idx) => (
          <tr key={idx}>
            {headers.map((head) => {
              const cellError =
                allowEdit && validationErrors.rows?.[idx]?.[head];

              return (
                <td
                  key={head}
                  className={cellError ? styles.invalidCell : ""}
                  title={cellError || ""}
                  {...(allowEdit && {
                    contentEditable: true,
                    suppressContentEditableWarning: true,
                    onBlur: (e) => handleCellEdit(e, idx, head),
                  })}
                >
                  {row[head]?.toString() || ""}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default DataTable;
