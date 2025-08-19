import React, { useEffect } from "react";
import "./App.module.scss";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Provider } from "react-redux";
import { store } from "./app/store/index";
import { SnackbarProvider } from "notistack";
import {
  Dashboard,
  Home,
  DefineNodeLabels,
  AttributeSummaryPage,
  ClusterMetricsPage,
  ClusterSummaryPage,
} from "./pages";
import { ThemeProvider } from "@mui/material/styles";
import { lightTheme, darkTheme } from "./utilis/theme";
import { useTheme } from "./hooks/useTheme";
import CustomTable from "./pages/custom-table";
import { PersistGate } from "redux-persist/integration/react";

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
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/:sessionId/" element={<Dashboard />} />
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
                  path="/define-node-labels"
                  element={<DefineNodeLabels />}
                />
              </Routes>
            </Router>
          </Provider>
        </SnackbarProvider>
      </ThemeProvider>
    </React.StrictMode>
  );
}

export default App;
