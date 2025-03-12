import React, { useEffect } from "react";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom"; // Import useNavigate
import * as AnalysisActions from "../app/store/kinfin/actions";

const Home = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate(); // Initialize navigate function

  useEffect(() => {
    dispatch(AnalysisActions.getRunStatus());
    dispatch(AnalysisActions.getAvailableAttributesTaxonsets());
    dispatch(AnalysisActions.getRunSummary());
    dispatch(AnalysisActions.getCountsByTaxon());
    dispatch(AnalysisActions.getClusterSummary({ attribute: "host" }));
    dispatch(AnalysisActions.getAttributeSummary({ attribute: "host" }));
    dispatch(
      AnalysisActions.getClusterMetrics({
        attribute: "host",
        taxonSet: "human",
      })
    );
  }, [dispatch]);

  const handleInitAnalysis = () => {
    dispatch(AnalysisActions.initAnalysis());
  };

  return (
    <>
      <div>
        <h1>KinFin Analysis</h1>
        <button onClick={handleInitAnalysis}>Analyze</button>
        <button onClick={() => navigate("/dashboard")}>Dashboard</button>
      </div>
    </>
  );
};

export default Home;
