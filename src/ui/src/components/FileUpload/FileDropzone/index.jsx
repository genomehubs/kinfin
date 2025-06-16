import React from "react";
import { MdOutlineFileUpload } from "react-icons/md";
import styles from "./FileDropZone.module.scss";

const FileDropZone = ({ onClick, selectedName, inputRef, onChange }) => (
  <div className={styles.uploadBox} onClick={onClick}>
    <p className={styles.icon}>
      <MdOutlineFileUpload />
    </p>
    <h3>{selectedName || "Click box to upload config"}</h3>
    <p>Maximum file size 10MB</p>
    <input
      type="file"
      ref={inputRef}
      accept=".csv,.tsv,.xls,.xlsx,.json"
      onChange={onChange}
      hidden
    />
  </div>
);

export default FileDropZone;
