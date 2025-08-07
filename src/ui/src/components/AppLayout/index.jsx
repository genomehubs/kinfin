import Sidebar from "../UIElements/Sidebar";
import styles from "./AppLayout.module.scss";
import { useState } from "react";
import Backdrop from "@mui/material/Backdrop";
import CircularProgress from "@mui/material/CircularProgress";
import { useSelector } from "react-redux";
import { useParams } from "react-router-dom";
import Navbar from "../Navbar";

const AppLayout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { sessionId } = useParams();
  const pollingLoadingBySessionId = useSelector(
    (state) => state.config.pollingLoadingBySessionId || {}
  );
  const isLoading = pollingLoadingBySessionId[sessionId];
  return (
    <>
      <Navbar onMenuClick={() => setSidebarOpen((prev) => !prev)} />

      <div className={styles.appLayout}>
        <Sidebar open={sidebarOpen} setOpen={setSidebarOpen} />
        <div
          suppressHydrationWarning={true}
          className={`${styles.childContainer} ${
            sidebarOpen ? "" : styles.closed
          }`}
        >
          {children}

          <Backdrop
            open={isLoading}
            sx={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              zIndex: (theme) => theme.zIndex.drawer + 1,
              color: "#fff",
              flexDirection: "column",
              gap: 2,
            }}
          >
            <CircularProgress color="inherit" />
            <div
              style={{ fontSize: "1.1rem", textAlign: "center", maxWidth: 300 }}
            >
              Initialization is in progress. <br />
              It might take 2–3 minutes. <br />
              Please wait…
            </div>
          </Backdrop>
        </div>
      </div>
    </>
  );
};

export default AppLayout;
