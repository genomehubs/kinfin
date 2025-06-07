import { takeEvery, fork, put, all, call } from "redux-saga/effects";

import {
  INIT_ANALYSIS,
  GET_RUN_STATUS,
  GET_AVAILABLE_ATTRIBUTES_TAXONSETS,
  GET_COUNTS_BY_TAXON,
  GET_CLUSTER_SUMMARY,
  GET_ATTRIBUTE_SUMMARY,
  GET_CLUSTER_METRICS,
  GET_PAIRWISE_ANALYSIS,
  GET_PLOT,
  GET_RUN_SUMMARY,
} from "./actionTypes";
import {
  initAnalysisSuccess,
  initAnalysisFailure,
  getRunStatusSuccess,
  getRunStatusFailure,
  getPlotSuccess,
  getPlotFailure,
  getPairwiseAnalysisSuccess,
  getPairwiseAnalysisFailure,
  getClusterMetricsSuccess,
  getClusterMetricsFailure,
  getAttributeSummarySuccess,
  getAttributeSummaryFailure,
  getClusterSummarySuccess,
  getClusterSummaryFailure,
  getCountsByTaxonSuccess,
  getCountsByTaxonFailure,
  getAvailableAttributesTaxonsetsSuccess,
  getAvailableAttributesTaxonsetsFailure,
  getRunSummaryFailure,
  getRunSummarySuccess,
  storeConfig,
} from "./actions";
import {
  dispatchErrorToast,
  dispatchSuccessToast,
} from "../../../utilis/tostNotifications";
import {
  initAnalysis,
  getAvailableAttributes,
  getStatus,
  getCountsByTaxon,
  getRunSummary,
  getClusterSummary,
  getAttributeSummary,
  getClusterMetrics,
  getPairwiseAnalysis,
  getPlot,
} from "../../services/client";

function* initAnalysisSaga(action) {
  const { name, config } = action.payload;
  try {
    const response = yield call(initAnalysis, config);
    if (response.status === "success") {
      yield put(initAnalysisSuccess(response.data));
      const payloadForIndexDBStorage = {
        name,
        config,
        sessionId: response.data.session_id,
      };
      yield put(storeConfig(payloadForIndexDBStorage));
      yield call(dispatchSuccessToast, "Analysis initialized successfully!");
    } else {
      yield put(initAnalysisFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error?.message || "Failed to initialize analysis"
      );
    }
  } catch (err) {
    yield put(initAnalysisFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error?.message || "Failed to initialize analysis"
    );
  }
}

function* getRunStatusSaga() {
  try {
    const response = yield call(getStatus);

    if (response.status === "success") {
      yield put(getRunStatusSuccess(response.data));
      yield call(dispatchSuccessToast, "Run status fetched successfully!");
    } else {
      yield put(getRunStatusFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error || "Failed to fetch run status"
      );
    }
  } catch (err) {
    yield put(getRunStatusFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Failed to fetch run status"
    );
  }
}
function* getAvailableAttributesSaga() {
  try {
    const response = yield call(getAvailableAttributes);

    if (response.status === "success") {
      yield put(getAvailableAttributesTaxonsetsSuccess(response.data));
      yield call(dispatchSuccessToast, "Attributes fetched successfully!");
    } else {
      yield put(getAvailableAttributesTaxonsetsFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error || "Failed to fetch attributes"
      );
    }
  } catch (err) {
    yield put(getAvailableAttributesTaxonsetsFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Failed to fetch attributes"
    );
  }
}
function* getRunSummarySaga() {
  try {
    const response = yield call(getRunSummary);

    if (response.status === "success") {
      yield put(getRunSummarySuccess(response.data));
      yield call(dispatchSuccessToast, "Run Summary fetched successfully!");
    } else {
      yield put(getRunSummaryFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error || "Failed to fetch run summary"
      );
    }
  } catch (err) {
    yield put(getRunSummaryFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Failed to fetch run summary"
    );
  }
}
function* getCountsByTaxonSaga() {
  try {
    const response = yield call(getCountsByTaxon);

    if (response.status === "success") {
      yield put(getCountsByTaxonSuccess(response.data));
      yield call(dispatchSuccessToast, "Counts by taxon fetched successfully!");
    } else {
      yield put(getCountsByTaxonFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error || "Failed to fetch Counts by taxon"
      );
    }
  } catch (err) {
    yield put(getCountsByTaxonFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Failed to fetch Counts by taxon"
    );
  }
}
function* getClusterSummarySaga(action) {
  const { attribute, page } = action.payload;
  const data = {
    attribute,
    size: 10,
    page,
  };
  try {
    const response = yield call(getClusterSummary, data);

    if (response.status === "success") {
      yield put(getClusterSummarySuccess(response));
      yield call(dispatchSuccessToast, "Cluster Summary fetched successfully!");
    } else {
      yield put(getClusterSummaryFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error || "Failed to fetch Cluster Summary"
      );
    }
  } catch (err) {
    yield put(getClusterSummaryFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Failed to fetch Cluster Summary"
    );
  }
}
function* getAttributeSummarySaga(action) {
  const { attribute, page } = action.payload;
  const data = {
    attribute,
    page,
    size: 10,
  };
  try {
    const response = yield call(getAttributeSummary, data);

    if (response.status === "success") {
      yield put(getAttributeSummarySuccess(response));
      yield call(
        dispatchSuccessToast,
        "Attribute Summary fetched successfully!"
      );
    } else {
      yield put(getAttributeSummaryFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error || "Failed to fetch Attribute Summary"
      );
    }
  } catch (err) {
    yield put(getAttributeSummaryFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Failed to fetch Attribute Summary"
    );
  }
}
function* getClusterMetricsSaga(action) {
  const { attribute, taxonSet, page } = action.payload;
  const data = {
    attribute,
    taxonSet,
    page,
    size: 10,
  };
  try {
    const response = yield call(getClusterMetrics, data);

    if (response.status === "success") {
      yield put(getClusterMetricsSuccess(response));
      yield call(dispatchSuccessToast, "Cluster Metrics fetched successfully!");
    } else {
      yield put(getClusterMetricsFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error || "Failed to fetch Cluster Metrics"
      );
    }
  } catch (err) {
    yield put(getClusterMetricsFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Failed to fetch Cluster Metrics"
    );
  }
}
function* getPairwiseAnalysisSaga(action) {
  const { attribute } = action.payload;
  try {
    const response = yield call(getPairwiseAnalysis, attribute);

    if (response.status === "success") {
      yield put(getPairwiseAnalysisSuccess(response.data));
      yield call(
        dispatchSuccessToast,
        "Pairwise Analysis fetched successfully!"
      );
    } else {
      yield put(getPairwiseAnalysisFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error || "Failed to fetch Pairwise Analysis"
      );
    }
  } catch (err) {
    yield put(getPairwiseAnalysisFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Failed to fetch Pairwise Analysis"
    );
  }
}

function* getPlotsSaga() {
  try {
    const [allRarefactionCurveBlob, clusterSizeDistributionBlob] = yield all([
      call(getPlot, "all-rarefaction-curve"),
      call(getPlot, "cluster-size-distribution"),
    ]);

    yield put(
      getPlotSuccess({
        allRarefactionCurve: allRarefactionCurveBlob,
        clusterSizeDistribution: clusterSizeDistributionBlob,
      })
    );
  } catch (error) {
    yield put(getPlotFailure(error));
    yield call(dispatchErrorToast, "Failed to fetch plots");
  }
}
export function* watchInitAnalysisSaga() {
  yield takeEvery(INIT_ANALYSIS, initAnalysisSaga);
}
export function* watchGetRunStatusSaga() {
  yield takeEvery(GET_RUN_STATUS, getRunStatusSaga);
}

export function* watchGetPlotsSaga() {
  yield takeEvery(GET_PLOT, getPlotsSaga);
}
export function* watchGetPairwiseAnalysisSaga() {
  yield takeEvery(GET_PAIRWISE_ANALYSIS, getPairwiseAnalysisSaga);
}
export function* watchGetClusterMetricsSaga() {
  yield takeEvery(GET_CLUSTER_METRICS, getClusterMetricsSaga);
}
export function* watchGetCountsByTaxonSaga() {
  yield takeEvery(GET_COUNTS_BY_TAXON, getCountsByTaxonSaga);
}
export function* watchGetAttributeSummarySaga() {
  yield takeEvery(GET_ATTRIBUTE_SUMMARY, getAttributeSummarySaga);
}
export function* watchGetClusterSummarySaga() {
  yield takeEvery(GET_CLUSTER_SUMMARY, getClusterSummarySaga);
}
export function* watchGetRunSummarySaga() {
  yield takeEvery(GET_RUN_SUMMARY, getRunSummarySaga);
}
export function* watchGetAvailableAttributesSaga() {
  yield takeEvery(
    GET_AVAILABLE_ATTRIBUTES_TAXONSETS,
    getAvailableAttributesSaga
  );
}

function* analysisSaga() {
  yield all([
    fork(watchInitAnalysisSaga),
    fork(watchGetRunStatusSaga),
    fork(watchGetAvailableAttributesSaga),
    fork(watchGetRunSummarySaga),
    fork(watchGetCountsByTaxonSaga),
    fork(watchGetClusterSummarySaga),
    fork(watchGetAttributeSummarySaga),
    fork(watchGetClusterMetricsSaga),
    fork(watchGetPairwiseAnalysisSaga),
    fork(watchGetPlotsSaga),
  ]);
}

export default analysisSaga;
