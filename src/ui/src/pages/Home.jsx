import React, { useEffect } from "react";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import {
  getRunStatus,
  getAvailableAttributesTaxonsets,
  getRunSummary,
  getCountsByTaxon,
  getClusterSummary,
  getAttributeSummary,
  getClusterMetrics,
  initAnalysis,
} from "../app/store/kinfin/actions";

const Home = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  useEffect(() => {
    dispatch(getRunStatus());
    dispatch(getAvailableAttributesTaxonsets());
    dispatch(getRunSummary());
    dispatch(getCountsByTaxon());
    dispatch(getClusterSummary({ attribute: "host" }));
    dispatch(getAttributeSummary({ attribute: "host" }));
    dispatch(
      getClusterMetrics({
        attribute: "host",
        taxonSet: "human",
      })
    );
  }, [dispatch]);

  const handleInitAnalysis = () => {
    dispatch(initAnalysis());
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
