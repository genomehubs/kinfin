import "./App.module.scss";

import {
  AttributeSummaryPage,
  ClusterMetricsPage,
  ClusterSizeDistributionPage,
  ClusterSummaryPage,
  DashboardPage,
  DefineNodeLabelsPage,
  Home,
  RarefactionCurvePage,
} from "./pages";
import { Provider, useSelector } from "react-redux";
import React, { useEffect, useRef } from "react";
import { Route, BrowserRouter as Router, Routes } from "react-router-dom";
import { darkTheme, lightTheme } from "./utils/theme";

import { SnackbarProvider } from "notistack";
import { ThemeProvider } from "@mui/material/styles";
import { store } from "#store/index";
import { useBatchStatus } from "#hooks/useBatchStatus.js";
import { useTheme } from "#hooks/useTheme";

/**
 * Inner component that refreshes persisted sessions on app startup.
 * Must be inside the Provider + Router context to use hooks.
 */
function AppWithSessionHydration() {
  const { theme } = useTheme();
  const [getBatchStatus] = useBatchStatus();
  const hasFetchedSessionsRef = useRef(false);

  // Get all persisted sessions from Redux state (loaded from localStorage by configSlice initialState)
  const allSessions = useSelector((state) => state?.config?.data || {});
  const sessionIds = Object.keys(allSessions);

  // Refresh metadata for all persisted sessions on app mount
  useEffect(() => {
    if (!hasFetchedSessionsRef.current && sessionIds.length > 0) {
      getBatchStatus(sessionIds);
      hasFetchedSessionsRef.current = true;
    }
  }, [sessionIds, getBatchStatus]);

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/:sessionId/" element={<DashboardPage />} />
      <Route
        path="/:sessionId/attribute-summary"
        element={<AttributeSummaryPage />}
      />
      <Route
        path="/:sessionId/cluster-summary"
        element={<ClusterSummaryPage />}
      />
      <Route
        path="/:sessionId/cluster-metrics"
        element={<ClusterMetricsPage />}
      />
      <Route
        path="/:sessionId/rarefaction-curve"
        element={<RarefactionCurvePage />}
      />
      <Route
        path="/:sessionId/cluster-size-distribution"
        element={<ClusterSizeDistributionPage />}
      />

      <Route path="/define-node-labels" element={<DefineNodeLabelsPage />} />
    </Routes>
  );
}

function App() {
  const { theme } = useTheme();
  useEffect(() => {
    const saved = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", saved);
  }, []);

  return (
    <React.StrictMode>
      <ThemeProvider theme={theme === "light" ? lightTheme : darkTheme}>
        <SnackbarProvider
          maxSnack={3}
          anchorOrigin={{
            vertical: "bottom",
            horizontal: "left",
          }}
          dense
          preventDuplicate
        >
          <Provider store={store}>
            <title>KinFin</title>
            <Router>
              <AppWithSessionHydration />
            </Router>
          </Provider>
        </SnackbarProvider>
      </ThemeProvider>
    </React.StrictMode>
  );
}

export default App;
