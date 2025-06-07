import Sidebar from "../UIElements/Sidebar";
import styles from "./AppLayout.module.scss";
import { useState } from "react";

const AppLayout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className={styles.appLayout}>
      <Sidebar open={sidebarOpen} setOpen={setSidebarOpen} />
      <div
        suppressHydrationWarning={true}
        className={`${styles.childContainer} ${
          sidebarOpen ? "" : styles.closed
        }`}
      >
        {children}
      </div>
    </div>
  );
};

export default AppLayout;
