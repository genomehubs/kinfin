import React, { useEffect } from "react";
import "./App.module.scss";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Provider } from "react-redux";
import { ToastContainer } from "react-toastify";
import { store, persistor } from "./app/store/index";
import { Dashboard, Home, DefineNodeLabels } from "./pages";
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
      <Provider store={store}>
        <PersistGate loading={null} persistor={persistor}>
          <ThemeProvider theme={theme === "light" ? lightTheme : darkTheme}>
            <title>KinFin</title>
            <Router>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route
                  path="/:sessionId/custom-table"
                  element={<CustomTable />}
                />
                <Route path="/:sessionId/dashboard" element={<Dashboard />} />
                <Route
                  path="/define-node-labels"
                  element={<DefineNodeLabels />}
                />
              </Routes>
            </Router>
            <ToastContainer />
          </ThemeProvider>
        </PersistGate>
      </Provider>
    </React.StrictMode>
  );
}

export default App;
