import React, { useRef } from "react";

import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import { Button } from "@mui/material";
import FullscreenExitIcon from "@mui/icons-material/FullscreenExit";
import FullscreenIcon from "@mui/icons-material/Fullscreen";
import IconButton from "@mui/material/IconButton";
import { MdOutlineFileDownload } from "react-icons/md";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import TuneIcon from "@mui/icons-material/Tune"; // Customise icon
import styles from "./ChartCard.module.scss";

const ChartCard = ({
  widthPercent = 100,
  title,
  isDownloading,
  onDownload,
  onOpen,
  onCustomise,
  onClose,
  children,
}) => {
  // add support for full screen view
  const fullScreenRef = useRef(null);
  const [isFullScreen, setIsFullScreen] = React.useState(false);

  const toggleFullScreen = () => {
    setIsFullScreen((prev) => !prev);
    if (!isFullScreen) {
      fullScreenRef.current.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  };

  const buttonSx = {
    borderRadius: "50px",
    textTransform: "none",
    fontSize: "0.9rem",
    padding: "6px 16px",
    minWidth: "auto",
  };

  return (
    <div
      className={styles.container}
      style={{
        flex: `1 1 ${widthPercent}%`,
        ...(isFullScreen ? { borderRadius: "0" } : {}),
      }}
      ref={fullScreenRef}
    >
      <div className={styles.header}>
        <div className={styles.titleContainer}>
          {onOpen && (
            <IconButton
              className={styles.enlargeButton}
              onClick={onOpen}
              size="small"
              title={"Open full page view"}
            >
              <OpenInNewIcon fontSize="small" />
            </IconButton>
          )}
          {onClose && (
            <IconButton
              onClick={onClose}
              size="small"
              sx={{ borderRadius: "50px" }}
              title={"Back to Previous Page"}
            >
              <ArrowBackIosNewIcon fontSize="small" />
            </IconButton>
          )}
          <p className={styles.title}>{title}</p>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          {onCustomise && (
            <Button
              variant="outlined"
              onClick={onCustomise}
              startIcon={<TuneIcon size={18} />}
              sx={buttonSx}
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
              sx={buttonSx}
            >
              Download
            </Button>
          )}
          {onClose && (
            <Button
              variant="outlined"
              onClick={toggleFullScreen}
              startIcon={
                isFullScreen ? (
                  <FullscreenExitIcon fontSize="small" />
                ) : (
                  <FullscreenIcon fontSize="small" />
                )
              }
              sx={buttonSx}
            >
              {isFullScreen ? "Exit Full Screen" : "Full Screen"}
            </Button>
          )}
        </div>
      </div>

      {children}
    </div>
  );
};

export default ChartCard;
