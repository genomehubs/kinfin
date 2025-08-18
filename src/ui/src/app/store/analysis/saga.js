import { takeEvery, fork, put, all, call, select } from "redux-saga/effects";
import { setDownloadLoading } from "../config/actions";

import {
  getAvailableAttributesTaxonsets,
  getAvailableAttributesTaxonsetsSuccess,
  getAvailableAttributesTaxonsetsFailure,
} from "./slices/availableAttributesTaxonsetsSlice";

import {
  getRunSummary,
  getRunSummarySuccess,
  getRunSummaryFailure,
} from "./slices/runSummarySlice";

import {
  getCountsByTaxon,
  getCountsByTaxonSuccess,
  getCountsByTaxonFailure,
} from "./slices/countsByTaxonSlice";

import {
  getClusterSummary,
  getClusterSummarySuccess,
  getClusterSummaryFailure,
} from "./slices/clusterSummarySlice";

import {
  getAttributeSummary,
  getAttributeSummarySuccess,
  getAttributeSummaryFailure,
} from "./slices/attributeSummarySlice";

import {
  getClusterMetrics,
  getClusterMetricsSuccess,
  getClusterMetricsFailure,
} from "./slices/clusterMetricsSlice";

import {
  getPairwiseAnalysis,
  getPairwiseAnalysisSuccess,
  getPairwiseAnalysisFailure,
} from "./slices/pairwiseAnalysisSlice";

import { getPlot, getPlotSuccess, getPlotFailure } from "./slices/plotSlice";

import { dispatchErrorToast } from "../../../utils/tostNotifications";
import {
  getAvailableAttributes,
  getCountsByTaxon as apiGetCountsByTaxon,
  getRunSummary as apiGetRunSummary,
  getClusterSummary as apiGetClusterSummary,
  getAttributeSummary as apiGetAttributeSummary,
  getClusterMetrics as apiGetClusterMetrics,
  getPairwiseAnalysis as apiGetPairwiseAnalysis,
  getPlot as apiGetPlot,
} from "../../services/client";
import { downloadBlobFile } from "../../../utils/downloadBlobFile";

const selectSessionStatusById = (session_id) => (state) =>
  state?.config?.storeConfig?.data?.[session_id]?.status;

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

    const response = yield call(apiGetRunSummary);
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

    const response = yield call(apiGetCountsByTaxon);
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
  const { attribute, page, size, asFile = false } = action.payload;
  const data = { attribute, size, page, asFile };

  try {
    const status = yield select(selectSessionStatusById(getSessionId()));
    if (!status) {
      return;
    }

    const response = yield call(apiGetClusterSummary, data);

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
  const { attribute, page, size, asFile = false } = action.payload;
  const data = { attribute, page, size, asFile };

  try {
    const status = yield select(selectSessionStatusById(getSessionId()));
    if (!status) {
      return;
    }

    const response = yield call(apiGetAttributeSummary, data);

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
  const { attribute, taxonSet, page, size, asFile = false } = action.payload;
  const data = { attribute, taxonSet, page, size, asFile };

  try {
    const status = yield select(selectSessionStatusById(getSessionId()));
    if (!status) {
      return;
    }

    const response = yield call(apiGetClusterMetrics, data);

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

    const response = yield call(apiGetPairwiseAnalysis, attribute);
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
      call(apiGetPlot, "all-rarefaction-curve"),
      call(apiGetPlot, "cluster-size-distribution"),
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

export function* watchGetAvailableAttributesSaga() {
  yield takeEvery(getAvailableAttributesTaxonsets, getAvailableAttributesSaga);
}
export function* watchGetRunSummarySaga() {
  yield takeEvery(getRunSummary, getRunSummarySaga);
}
export function* watchGetCountsByTaxonSaga() {
  yield takeEvery(getCountsByTaxon, getCountsByTaxonSaga);
}
export function* watchGetClusterSummarySaga() {
  yield takeEvery(getClusterSummary, getClusterSummarySaga);
}
export function* watchGetAttributeSummarySaga() {
  yield takeEvery(getAttributeSummary, getAttributeSummarySaga);
}
export function* watchGetClusterMetricsSaga() {
  yield takeEvery(getClusterMetrics, getClusterMetricsSaga);
}
export function* watchGetPairwiseAnalysisSaga() {
  yield takeEvery(getPairwiseAnalysis, getPairwiseAnalysisSaga);
}
export function* watchGetPlotsSaga() {
  yield takeEvery(getPlot, getPlotsSaga);
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
