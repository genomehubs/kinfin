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
import React, { useEffect } from "react";
import { Route, BrowserRouter as Router, Routes } from "react-router-dom";
import { darkTheme, lightTheme } from "./utils/theme";

import { PersistGate } from "redux-persist/integration/react";
import { Provider } from "react-redux";
import { SnackbarProvider } from "notistack";
import { ThemeProvider } from "@mui/material/styles";
import { store } from "#store/index";
import { useTheme } from "#hooks/useTheme";

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
            <PersistGate persistor={persistor} loading={null}>
              <title>KinFin</title>
              <Router>
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

                  <Route
                    path="/define-node-labels"
                    element={<DefineNodeLabelsPage />}
                  />
                </Routes>
              </Router>
            </PersistGate>
          </Provider>
        </SnackbarProvider>
      </ThemeProvider>
    </React.StrictMode>
  );
}

export default App;
