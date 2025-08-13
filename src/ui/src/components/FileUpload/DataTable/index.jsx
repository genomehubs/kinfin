import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
} from "@mui/material";
import styles from "./DataTable.module.scss";

const DataTable = ({
  parsedData,
  validationErrors = { headers: [], rows: [] },
  handleHeaderEdit = () => {},
  handleCellEdit = () => {},
  allowEdit = true,
}) => {
  if (!Array.isArray(parsedData)) {
    return <Typography>Data is not in tabular format.</Typography>;
  }
  if (parsedData.length === 0) {
    return <Typography>No data to display.</Typography>;
  }

  const headers = Object.keys(parsedData[0]);

  return (
    <TableContainer
      component={Paper}
      sx={{
        maxHeight: 300,
        overflowY: "auto",
      }}
    >
      <Table stickyHeader size="small">
        <TableHead>
          <TableRow>
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
                <TableCell
                  key={head}
                  className={hasHeaderError ? styles.invalidHeader : ""}
                  title={hasHeaderError ? headerErrorMsg : ""}
                  sx={{ fontWeight: "bold", backgroundColor: "var(--th-bg)" }}
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
                    head
                  )}
                </TableCell>
              );
            })}
          </TableRow>
        </TableHead>
        <TableBody>
          {parsedData.map((row, idx) => (
            <TableRow key={idx}>
              {headers.map((head) => {
                const cellError =
                  allowEdit && validationErrors.rows?.[idx]?.[head];

                return (
                  <TableCell
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
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default DataTable;
