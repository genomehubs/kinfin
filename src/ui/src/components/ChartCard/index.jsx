import React from "react";
import styles from "./ChartCard.module.scss";
import { MdOutlineFileDownload } from "react-icons/md";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import TuneIcon from "@mui/icons-material/Tune"; // Customise icon
import Button from "@mui/material/Button";

const ChartCard = ({
  widthPercent = 100,
  title,
  isDownloading,
  onDownload,
  onOpen,
  onCustomise,
  children,
}) => {
  return (
    <div
      className={styles.container}
      style={{ flex: `1 1 ${widthPercent}%`, maxWidth: `${widthPercent}%` }}
    >
      <div className={styles.header}>
        <div className={styles.titleContainer}>
          {onOpen && (
            <button className={styles.enlargeButton} onClick={onOpen}>
              <OpenInNewIcon fontSize="small" />
            </button>
          )}
          <p className={styles.title}>{title}</p>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          {onCustomise && (
            <Button
              variant="outlined"
              onClick={onCustomise}
              startIcon={<TuneIcon size={18} />}
              sx={{
                borderRadius: "50px",
                textTransform: "none",
                fontSize: "0.9rem",
                padding: "6px 16px",
                minWidth: "auto",
              }}
            >
              Customise
            </Button>
          )}

          {onDownload && (
            <Button
              variant="outlined"
              onClick={onDownload}
              disabled={isDownloading}
              startIcon={
                isDownloading ? (
                  <div className={styles.downloadLoader} />
                ) : (
                  <MdOutlineFileDownload size={18} />
                )
              }
              sx={{
                borderRadius: "50px",
                textTransform: "none",
                fontSize: "0.9rem",
                padding: "6px 16px",
                minWidth: "auto",
              }}
            >
              Download
            </Button>
          )}
        </div>
      </div>

      {children}
    </div>
  );
};

export default ChartCard;
