import React from "react";
import styles from "./ValidationErrors.module.scss";

const ValidationErrors = ({ validationErrors }) => {
  const hasHeaders = validationErrors.headers.length > 0;
  const hasRows = Object.keys(validationErrors.rows).length > 0;

  if (!hasHeaders && !hasRows) {
    return null;
  }

  return (
    <div className={styles.errorMessage}>
      {hasHeaders && (
        <>
          <p>Header validation issues:</p>
          <ul>
            {validationErrors.headers.map((msg, i) => (
              <li key={i}>{msg}</li>
            ))}
          </ul>
        </>
      )}
      {hasRows && (
        <>
          <p>Row validation issues:</p>
          <ul>
            {Object.entries(validationErrors.rows).map(([rowIndex, errors]) => (
              <li key={rowIndex}>
                Row {parseInt(rowIndex) + 1}:
                <ul>
                  {Object.entries(errors).map(([field, errorMsg], i) => (
                    <li key={i}>
                      <strong>{field}:</strong> {errorMsg}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
};

export default ValidationErrors;
