import React from "react";
import styles from "./ChartCard.module.scss";
import { MdOutlineFileDownload } from "react-icons/md";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";

const ChartCard = ({ title, isDownloading, onDownload, onOpen, children }) => {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        {onOpen && (
          <button className={styles.enlargeButton} onClick={onOpen}>
            <OpenInNewIcon fontSize="small" />
          </button>
        )}
        {onDownload && (
          <button
            className={styles.enlargeButton}
            onClick={onDownload}
            disabled={isDownloading}
          >
            {isDownloading ? (
              <div className={styles.downloadLoader} />
            ) : (
              <MdOutlineFileDownload />
            )}
          </button>
        )}
        <p className={styles.title}>{title}</p>
      </div>
      {children}
    </div>
  );
};

export default ChartCard;
