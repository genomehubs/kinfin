import { combineReducers } from "redux";
import analysisReducer from "./analysis/reducers";
import configReducer from "./config/reducers";

// --- slices ---
import runSummaryReducer from "./analysis/slices/runSummarySlice";
import availableAttributesReducer from "./analysis/slices/availableAttributesTaxonsetsSlice";
import countsByTaxonReducer from "./analysis/slices/countsByTaxonSlice";
import clusterSummaryReducer from "./analysis/slices/clusterSummarySlice";
import attributeSummaryReducer from "./analysis/slices/attributeSummarySlice";
import clusterMetricsReducer from "./analysis/slices/clusterMetricsSlice";
import pairwiseAnalysisReducer from "./analysis/slices/pairwiseAnalysisSlice";
import plotReducer from "./analysis/slices/plotSlice";

const rootReducer = combineReducers({
  oldAnalysis: analysisReducer,
  config: configReducer,

  analysis: combineReducers({
    runSummary: runSummaryReducer,
    availableAttributesTaxonsets: availableAttributesReducer,
    countsByTaxon: countsByTaxonReducer,
    clusterSummary: clusterSummaryReducer,
    attributeSummary: attributeSummaryReducer,
    clusterMetrics: clusterMetricsReducer,
    pairwiseAnalysis: pairwiseAnalysisReducer,
    plot: plotReducer,
  }),
});

export default rootReducer;
