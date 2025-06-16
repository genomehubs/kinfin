import React from "react";
import styles from "./JsonEditor.module.scss";

const JsonEditor = ({ jsonText, onChange, jsonError }) => (
  <>
    <h4>Parsed JSON (editable):</h4>
    <textarea
      className={styles.jsonTextarea}
      value={jsonText}
      onChange={onChange}
      spellCheck={false}
    />
    {jsonError && <p className={styles.errorMessage}>{jsonError}</p>}
  </>
);

export default JsonEditor;
