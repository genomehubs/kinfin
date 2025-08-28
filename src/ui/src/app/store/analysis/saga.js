import { all, call, fork, put, select, takeEvery } from "redux-saga/effects";
import {
  getAttributeSummary as apiGetAttributeSummary,
  getClusterMetrics as apiGetClusterMetrics,
  getClusterSummary as apiGetClusterSummary,
  getCountsByTaxon as apiGetCountsByTaxon,
  getPairwiseAnalysis as apiGetPairwiseAnalysis,
  getPlot as apiGetPlot,
  getRunSummary as apiGetRunSummary,
  getAvailableAttributes,
} from "../../services/client";
import {
  getAttributeSummary,
  getAttributeSummaryFailure,
  getAttributeSummarySuccess,
} from "./slices/attributeSummarySlice";
import {
  getAvailableAttributesTaxonsets,
  getAvailableAttributesTaxonsetsFailure,
  getAvailableAttributesTaxonsetsSuccess,
} from "./slices/availableAttributesTaxonsetsSlice";
import {
  getClusterMetrics,
  getClusterMetricsFailure,
  getClusterMetricsSuccess,
} from "./slices/clusterMetricsSlice";
import {
  getClusterSummary,
  getClusterSummaryFailure,
  getClusterSummarySuccess,
} from "./slices/clusterSummarySlice";
import {
  getCountsByTaxon,
  getCountsByTaxonFailure,
  getCountsByTaxonSuccess,
} from "./slices/countsByTaxonSlice";
import {
  getPairwiseAnalysis,
  getPairwiseAnalysisFailure,
  getPairwiseAnalysisSuccess,
} from "./slices/pairwiseAnalysisSlice";
import { getPlot, getPlotFailure, getPlotSuccess } from "./slices/plotSlice";
import {
  getRunSummary,
  getRunSummaryFailure,
  getRunSummarySuccess,
} from "./slices/runSummarySlice";

import { dispatchErrorToast } from "../../../utils/toastNotifications";
import { downloadBlobFile } from "../../../utils/downloadBlobFile";
import { setDownloadLoading } from "../config/slices/uiStateSlice";

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

function* getPlotsSaga(action) {
  const { attribute = "all" } = action.payload;
  try {
    const status = yield select(selectSessionStatusById(getSessionId()));
    if (!status) {
      return;
    }

    const [rarefactionCurveBlob, clusterSizeDistributionBlob] = yield all([
      call(apiGetPlot, { plotType: "rarefaction-curve", attribute }),
      call(apiGetPlot, { plotType: "cluster-size-distribution", attribute }),
    ]);

    yield put(
      getPlotSuccess({
        rarefactionCurve: rarefactionCurveBlob,
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
