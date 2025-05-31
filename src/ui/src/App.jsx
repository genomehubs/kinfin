import React from "react";
import "./App.module.scss";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Provider } from "react-redux";
import { ToastContainer } from "react-toastify";
import { store } from "./app/store/index";
import { Dashboard, Home, DefineNodeLabels } from "./pages";

function App() {
  return (
    <React.StrictMode>
      <Provider store={store}>
        <Router>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/define-node-labels" element={<DefineNodeLabels />} />
          </Routes>
        </Router>
        <ToastContainer />
      </Provider>
    </React.StrictMode>
  );
}

export default App;
