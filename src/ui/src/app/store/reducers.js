import { combineReducers } from "redux";
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

import analysisReducer from "./config/slices/analysisSlice";
import runStatusReducer from "./config/slices/runStatusSlice";
import configSliceReducer from "./config/slices/configSlice";
import proteomeIdsReducer from "./config/slices/proteomeIdsSlice";
import uiStateReducer from "./config/slices/uiStateSlice";
import batchStatusReducer from "./config/slices/batchStatusSlice";
import clusteringSetsReducer from "./config/slices/clusteringSetsSlice";

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
