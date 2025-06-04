import React, { useState, useEffect } from "react";
import styles from "./Sidebar.module.scss";
import { FiMenu, FiDownload } from "react-icons/fi";
import { GoKebabHorizontal } from "react-icons/go";
import { useSelector } from "react-redux";
import { useTheme } from "../../../hooks/useTheme";

const Sidebar = ({ open, setOpen }) => {
  const { theme, toggleTheme } = useTheme();
  const defaultItem = { label: "New Analysis", isNew: true };
  const analysisConfigs = useSelector(
    (state) => state?.analysis?.storeConfig?.data
  );
  const analysisList = analysisConfigs && Object?.values(analysisConfigs);

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
            <div className={`${styles.menuItem} ${styles.newAnalysis}`}>
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
                <div key={item.id} className={styles.menuItem}>
                  <span className={styles.label}>{item.name}</span>
                  <GoKebabHorizontal className={styles.downloadIcon} />
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
