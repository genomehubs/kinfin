import { takeEvery, fork, put, all, call, select } from "redux-saga/effects";

import {
  GET_AVAILABLE_ATTRIBUTES_TAXONSETS,
  GET_COUNTS_BY_TAXON,
  GET_CLUSTER_SUMMARY,
  GET_ATTRIBUTE_SUMMARY,
  GET_CLUSTER_METRICS,
  GET_PAIRWISE_ANALYSIS,
  GET_PLOT,
  GET_RUN_SUMMARY,
} from "./actionTypes";
import { setDownloadLoading } from "../config/actions";
import {
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
} from "./actions";
import { dispatchErrorToast } from "../../../utilis/tostNotifications";
import {
  getAvailableAttributes,
  getCountsByTaxon,
  getRunSummary,
  getClusterSummary,
  getAttributeSummary,
  getClusterMetrics,
  getPairwiseAnalysis,
  getPlot,
} from "../../services/client";

import { downloadBlobFile } from "../../../utilis/downloadBlobFile";
const selectSessionStatusById = (session_id) => (state) => {
  return state?.config?.storeConfig?.data?.[session_id]?.status;
};

const getSessionId = () =>
  localStorage.getItem("currentSessionId") ||
  "6599179a64accf331ffe653db00a0e24";

function* getAvailableAttributesSaga() {
  try {
    const status = yield select(selectSessionStatusById(getSessionId()));

    if (!status) {
      return;
    }

    const response = yield call(getAvailableAttributes);

    if (response.status === "success") {
      yield put(getAvailableAttributesTaxonsetsSuccess(response.data));
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
    const status = yield select(selectSessionStatusById(getSessionId()));

    if (!status) {
      return;
    }
    const response = yield call(getRunSummary);

    if (response.status === "success") {
      yield put(getRunSummarySuccess(response.data));
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
    const status = yield select(selectSessionStatusById(getSessionId()));

    if (!status) {
      return;
    }
    const response = yield call(getCountsByTaxon);

    if (response.status === "success") {
      yield put(getCountsByTaxonSuccess(response.data));
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
  const { attribute, page, size, asFile = false, CS_code } = action.payload;
  const data = {
    attribute,
    size,
    page,
    asFile,
    CS_code,
  };
  try {
    const status = yield select(selectSessionStatusById(getSessionId()));

    if (!status) {
      return;
    }
    const response = yield call(getClusterSummary, data);

    if (asFile) {
      yield call(
        downloadBlobFile,
        response,
        `${attribute}_cluster_summary.tsv`,
        "text/tab-separated-values"
      );
      if (setDownloadLoading) {
        yield put(
          setDownloadLoading({ type: "clusterSummary", loading: false })
        );
      }

      return;
    }

    if (response.status === "success") {
      yield put(getClusterSummarySuccess(response));
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
  const { attribute, page, size, asFile = false, AS_code } = action.payload;
  const data = {
    attribute,
    page,
    size,
    asFile,
    AS_code,
  };
  try {
    const status = yield select(selectSessionStatusById(getSessionId()));

    if (!status) {
      return;
    }
    const response = yield call(getAttributeSummary, data);

    if (asFile) {
      yield call(
        downloadBlobFile,
        response,
        `${attribute}_attribute_summary.tsv`,
        "text/tab-separated-values"
      );
      if (setDownloadLoading) {
        yield put(
          setDownloadLoading({ type: "attributeSummary", loading: false })
        );
      }
      return;
    }

    if (response.status === "success") {
      yield put(getAttributeSummarySuccess(response));
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
  const {
    attribute,
    taxonSet,
    page,
    size,
    asFile = false,
    CM_code,
  } = action.payload;
  const data = {
    attribute,
    taxonSet,
    page,
    size,
    asFile,
    CM_code,
  };
  try {
    const status = yield select(selectSessionStatusById(getSessionId()));

    if (!status) {
      return;
    }
    const response = yield call(getClusterMetrics, data);

    if (asFile) {
      yield call(
        downloadBlobFile,
        response,
        `${attribute}_${taxonSet}_cluster_metrics.tsv`,
        "text/tab-separated-values"
      );
      if (setDownloadLoading) {
        yield put(
          setDownloadLoading({ type: "clusterMetrics", loading: false })
        );
      }
      return;
    }

    if (response.status === "success") {
      yield put(getClusterMetricsSuccess(response));
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
    const status = yield select(selectSessionStatusById(getSessionId()));

    if (!status) {
      return;
    }
    const response = yield call(getPairwiseAnalysis, attribute);

    if (response.status === "success") {
      yield put(getPairwiseAnalysisSuccess(response.data));
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
    const status = yield select(selectSessionStatusById(getSessionId()));

    if (!status) {
      return;
    }
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
