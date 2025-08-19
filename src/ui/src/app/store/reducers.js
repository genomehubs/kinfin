import { combineReducers } from "redux";

// --- slices ---
import attributeSummaryReducer from "./analysis/slices/attributeSummarySlice";
import availableAttributesReducer from "./analysis/slices/availableAttributesTaxonsetsSlice";
import clusterMetricsReducer from "./analysis/slices/clusterMetricsSlice";
import clusterSummaryReducer from "./analysis/slices/clusterSummarySlice";
import countsByTaxonReducer from "./analysis/slices/countsByTaxonSlice";
import pairwiseAnalysisReducer from "./analysis/slices/pairwiseAnalysisSlice";
import plotReducer from "./analysis/slices/plotSlice";
import runSummaryReducer from "./analysis/slices/runSummarySlice";

import analysisReducer from "./config/slices/analysisSlice";
import batchStatusReducer from "./config/slices/batchStatusSlice";
import clusteringSetsReducer from "./config/slices/clusteringSetsSlice";
import configSliceReducer from "./config/slices/configSlice";
import proteomeIdsReducer from "./config/slices/proteomeIdsSlice";
import runStatusReducer from "./config/slices/runStatusSlice";
import uiStateReducer from "./config/slices/uiStateSlice";

const rootReducer = combineReducers({
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

  config: combineReducers({
    initAnalysis: analysisReducer,
    runStatus: runStatusReducer,
    validProteomeIds: proteomeIdsReducer,
    uiState: uiStateReducer,
    batchStatus: batchStatusReducer,
    clusteringSets: clusteringSetsReducer,
    storeConfig: configSliceReducer,
  }),
});

export default rootReducer;
