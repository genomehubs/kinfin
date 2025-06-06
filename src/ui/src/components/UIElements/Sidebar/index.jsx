import React, { useState, useEffect, useRef } from "react";
import styles from "./Sidebar.module.scss";
import { FiMenu, FiDownload } from "react-icons/fi";
import { GoKebabHorizontal } from "react-icons/go";
import { useSelector } from "react-redux";
import { useTheme } from "../../../hooks/useTheme";
import { useNavigate } from "react-router-dom";
import Tooltip from "rc-tooltip";
import "rc-tooltip/assets/bootstrap.css";
import { AiFillDelete } from "react-icons/ai";

import { MdOutlineEdit } from "react-icons/md";

const Sidebar = ({ open, setOpen }) => {
  const { theme, toggleTheme } = useTheme();
  const [visibleTooltip, setVisibleTooltip] = useState(null);
  const navigate = useNavigate();
  const defaultItem = { label: "New Analysis", isNew: true };
  const analysisConfigs = useSelector(
    (state) => state?.analysis?.storeConfig?.data
  );
  const analysisList = analysisConfigs && Object?.values(analysisConfigs);
  const tooltipRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (tooltipRef.current && !tooltipRef.current.contains(event.target)) {
        setVisibleTooltip(null);
      }
    };

    if (visibleTooltip !== null) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [visibleTooltip]);

  return (
    <>
      <div className={`${styles.sidebar} ${open ? "" : styles.closed}`}>
        <div className={styles.top}>
          <h2>Kinfin</h2>
          <button className={styles.toggleBtn} onClick={() => setOpen(false)}>
            <FiMenu />
          </button>
        </div>

        <div className={styles.menu}>
          {/* Default item */}
          <div className={styles.defaultSection}>
            <div
              onClick={() => navigate(`/define-node-labels`)}
              className={`${styles.menuItem} ${styles.newAnalysis}`}
            >
              <span className={styles.label}>{defaultItem.label}</span>
            </div>
          </div>

          <div className={styles.divider}></div>

          {/* Analysis list */}
          <div className={styles.otherSection}>
            {analysisList?.length === 0 ? (
              <div className={styles.emptyState}>No saved analyses</div>
            ) : (
              analysisList?.map((item) => (
                <div
                  key={item.sessionId}
                  className={`${styles.menuItem} ${
                    visibleTooltip === item.sessionId ? styles.active : ""
                  }`}
                  onClick={() => navigate(`/${item.sessionId}/dashboard`)} // or define-node-labels
                >
                  <span className={styles.label}>{item.name}</span>
                  <div className={styles.refContainer} ref={tooltipRef}>
                    <Tooltip
                      placement="rightTop"
                      overlay={
                        <div className={styles.tooltipContent}>
                          <div
                            className={styles.tooltipItem}
                            onClick={(e) => {
                              e.stopPropagation();
                              console.log(
                                "Download clicked for:",
                                item.sessionId
                              );
                            }}
                          >
                            <FiDownload className={styles.icon} /> Download
                          </div>
                          <div
                            className={styles.tooltipItem}
                            onClick={(e) => {
                              e.stopPropagation();
                              console.log(
                                "Rename clicked for:",
                                item.sessionId
                              );
                            }}
                          >
                            <MdOutlineEdit />
                            Rename
                          </div>
                          <div
                            className={styles.tooltipItem}
                            onClick={(e) => {
                              e.stopPropagation();
                              console.log(
                                "Delete clicked for:",
                                item.sessionId
                              );
                            }}
                          >
                            <AiFillDelete />
                            Delete
                          </div>
                        </div>
                      }
                      visible={visibleTooltip === item.sessionId}
                      showArrow={false}
                      trigger={[]}
                    >
                      <GoKebabHorizontal
                        className={styles.downloadIcon}
                        onClick={(e) => {
                          e.stopPropagation();
                          setVisibleTooltip((prev) =>
                            prev === item.sessionId ? null : item.sessionId
                          );
                        }}
                      />
                    </Tooltip>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
        <div className={styles.bottom}>
          <button onClick={toggleTheme} className={styles.toggleTheme}>
            Switch to {theme === "light" ? "Dark" : "Light"} Mode
          </button>
        </div>
      </div>

      {!open && (
        <button className={styles.floatingToggle} onClick={() => setOpen(true)}>
          <FiMenu />
        </button>
      )}
    </>
  );
};

export default Sidebar;
