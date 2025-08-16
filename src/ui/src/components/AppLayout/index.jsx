import { useLocation, Link } from "react-router-dom";
import { breadcrumbMap } from "../../utilis/breadcrumbConfig";
import Navbar from "../Navbar";
import Sidebar from "../UIElements/Sidebar";
import styles from "./AppLayout.module.scss";
import { useState } from "react";
import Backdrop from "@mui/material/Backdrop";
import CircularProgress from "@mui/material/CircularProgress";
import { useSelector } from "react-redux";
import { useParams } from "react-router-dom";

const AppLayout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { sessionId } = useParams();
  const { pathname } = useLocation();

  const analysisConfigs = useSelector(
    (state) => state?.config?.storeConfig?.data
  );
  const analysisList = analysisConfigs && Object?.values(analysisConfigs);
  console.log("🚀 ~ AppLayout ~ analysisList:", analysisList);

  const sessionMetaMap = {};
  analysisList?.forEach((item) => {
    sessionMetaMap[item.sessionId] = {
      name: item.name,
      clusterName: item.clusterName || "Unassigned Cluster",
    };
  });
  console.log("🚀 ~ AppLayout ~ sessionMetaMap:", sessionMetaMap);

  const pathSegments = pathname.split("/").filter(Boolean);
  const breadcrumbItems = pathSegments.map((segment, index) => {
    let label = breadcrumbMap[segment] || segment;

    if (sessionMetaMap[segment]) {
      const { name, clusterName } = sessionMetaMap[segment];
      label = `${name} (${clusterName})`;
    }

    const url = "/" + pathSegments.slice(0, index + 1).join("/");
    return {
      label,
      href: index < pathSegments.length - 1 ? url : undefined,
    };
  });

  const pollingLoadingBySessionId = useSelector(
    (state) => state.config.pollingLoadingBySessionId || {}
  );
  const isLoading = pollingLoadingBySessionId[sessionId];

  return (
    <>
      <Navbar
        onMenuClick={() => setSidebarOpen((prev) => !prev)}
        breadcrumbs={breadcrumbItems}
      />
      <div className={styles.appLayout}>
        <Sidebar open={sidebarOpen} setOpen={setSidebarOpen} />
        <div
          suppressHydrationWarning={true}
          className={`${styles.childContainer} ${
            sidebarOpen ? "" : styles.closed
          }`}
        >
          {children}

          {isLoading && (
            <Backdrop
              open={true}
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
                style={{
                  fontSize: "1.1rem",
                  textAlign: "center",
                  maxWidth: 300,
                }}
              >
                Initialization is in progress. <br />
                It might take 2–3 minutes. <br />
                Please wait…
              </div>
            </Backdrop>
          )}
        </div>
      </div>
    </>
  );
};

export default AppLayout;
