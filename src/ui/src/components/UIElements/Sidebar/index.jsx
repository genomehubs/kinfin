import React, { useState } from "react";
import styles from "./Sidebar.module.scss";
import { FiMenu, FiLogOut, FiDownload } from "react-icons/fi";

const Sidebar = ({ open, setOpen }) => {
  const defaultItem = { label: "New Analysis", isNew: true };
  const otherItems = [
    { label: "Nematode Host Associations" },
    { label: "Bacterial Pathogenicity Study" },
    { label: "Plant Environmental Adaptation" },
  ];

  return (
    <>
      <div className={`${styles.sidebar} ${!open ? styles.closed : ""}`}>
        <div className={styles.top}>
          <h2>Kinfin</h2>
          <button className={styles.toggleBtn} onClick={() => setOpen(false)}>
            <FiMenu />
          </button>
        </div>

        <div className={styles.menu}>
          {/* Default single item section */}
          <div className={styles.defaultSection}>
            <div className={`${styles.menuItem} ${styles.newAnalysis}`}>
              <span className={styles.label}>{defaultItem.label}</span>
            </div>
          </div>

          {/* Divider line */}
          <div className={styles.divider}></div>

          {/* Other menu items section */}
          <div className={styles.otherSection}>
            {otherItems.map((item, idx) => (
              <div key={idx} className={styles.menuItem}>
                <span className={styles.label}>{item.label}</span>
                <FiDownload className={styles.downloadIcon} />
              </div>
            ))}
          </div>
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
