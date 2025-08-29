import {
  all,
  call,
  delay,
  fork,
  put,
  select,
  takeEvery,
} from "redux-saga/effects";
import {
  dispatchErrorToast,
  dispatchSuccessToast,
} from "../../../utils/toastNotifications";
import {
  getBatchStatus,
  getBatchStatusFailure,
  getBatchStatusSuccess,
} from "./slices/batchStatusSlice";
import {
  getBatchStatus as getBatchStatusApi,
  getClusteringSets as getClusteringSetsApi,
  getColumnDescriptions as getColumnDescriptionsApi,
  getStatus as getStatusApi,
  getValidProteomeIds as getValidProteomeIdsApi,
  initAnalysis as initAnalysisApi,
} from "../../services/client";
import {
  getClusteringSets,
  getClusteringSetsFailure,
  getClusteringSetsSuccess,
} from "./slices/clusteringSetsSlice";
import {
  getColumnDescriptions,
  getColumnDescriptionsFailure,
  getColumnDescriptionsSuccess,
} from "./slices/columnDescriptionsSlice";
import {
  getRunStatus,
  getRunStatusFailure,
  getRunStatusSuccess,
} from "./slices/runStatusSlice";
import {
  getValidProteomeIds,
  getValidProteomeIdsFailure,
  getValidProteomeIdsSuccess,
} from "./slices/proteomeIdsSlice";
// --- slice actions ---
import {
  initAnalysis,
  initAnalysisFailure,
  initAnalysisSuccess,
} from "./slices/analysisSlice";
import { storeConfig, updateSessionMeta } from "./slices/configSlice";

import { fastIsEqual } from "fast-is-equal";
import { setPollingLoading } from "./slices/uiStateSlice";

// --- constants ---
const POLLING_INTERVAL = 5000; // 5 seconds
const MAX_POLLING_ATTEMPTS = 120; // 10 minutes

// --- selectors ---
const selectSessionStatusById = (session_id) => (state) => {
  return state?.config?.configMain?.data?.[session_id]?.status;
};

const getSessionId = () =>
  localStorage.getItem("currentSessionId") ||
  "6599179a64accf331ffe653db00a0e24";

// --- sagas ---
function* pollRunStatusSaga(sessionId) {
  yield put(setPollingLoading({ sessionId, loading: true }));
  try {
    let isComplete = false;
    let attempts = 0;

    while (!isComplete && attempts < MAX_POLLING_ATTEMPTS) {
      const response = yield call(getStatusApi, sessionId);

      if (response.status === "success") {
        const statusData = response.data;
        yield put(getRunStatusSuccess(statusData));

        if (statusData.is_complete) {
          isComplete = true;
          yield call(dispatchSuccessToast, "Analysis completed!");
          yield fork(getBatchStatusSaga, {
            payload: { sessionIds: [sessionId] },
          });
        }
      } else {
        yield put(getRunStatusFailure(response));
        yield call(
          dispatchErrorToast,
          response?.error || "Failed to fetch run status"
        );
      }

      attempts++;
      if (!isComplete) {
        yield delay(POLLING_INTERVAL);
      }
    }

    if (attempts >= MAX_POLLING_ATTEMPTS && !isComplete) {
      yield call(dispatchErrorToast, "Polling timed out after 10 minutes.");
    }
  } catch (err) {
    yield put(getRunStatusFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Polling failed"
    );
  } finally {
    yield put(setPollingLoading({ sessionId, loading: false }));
  }
}

function* initAnalysisSaga(action) {
  const { name, config, navigate, clusterId, clusterName } = action.payload;
  const data = { config, clusterId };

  try {
    const response = yield call(initAnalysisApi, data);
    if (response.status === "success") {
      yield put(initAnalysisSuccess(response.data));
      const payloadForIndexDBStorage = {
        name,
        config,
        sessionId: response.data.session_id,
        clusterId,
        clusterName,
      };
      yield put(storeConfig(payloadForIndexDBStorage));
      yield call(navigate, `/${response.data.session_id}`);
      yield fork(pollRunStatusSaga, response.data.session_id);
    } else {
      yield put(initAnalysisFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error?.message || "Failed to initialize analysis"
      );
    }
  } catch (err) {
    yield put(initAnalysisFailure(err));
    console.error(err);
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error?.message || "Failed to initialize analysis"
    );
  }
}

function* getRunStatusSaga() {
  try {
    const status = yield select(selectSessionStatusById(getSessionId()));
    if (!status) {
      return;
    }

    const response = yield call(getStatusApi);
    if (response.status === "success") {
      yield put(getRunStatusSuccess(response.data));
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

function* getValidProteomeIdsSaga(action) {
  const { clusterId } = action.payload;
  let allData = [];
  let page = 1;
  let totalPages = 1;
  try {
    do {
      const data = { page, size: 100, clusterId };
      const response = yield call(getValidProteomeIdsApi, data);

      if (response.status === "success") {
        if (page === 1) {
          totalPages = response.total_pages || 1;
        }
        allData = { ...allData, ...response.data };
        page++;
      } else {
        yield put(getValidProteomeIdsFailure(response));
        yield call(
          dispatchErrorToast,
          response?.error || "Failed to fetch valid proteome IDs"
        );
        break;
      }
    } while (page <= totalPages);

    if (Object.keys(allData).length > 0) {
      yield put(getValidProteomeIdsSuccess(allData));
    }
  } catch (err) {
    yield put(getValidProteomeIdsFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Failed to fetch valid proteome IDs"
    );
  }
}
export function* getBatchStatusSaga(action) {
  const { sessionIds } = action.payload;
  try {
    const response = yield call(getBatchStatusApi, sessionIds);
    if (response.status === "success") {
      yield put(getBatchStatusSuccess(response.data));

      for (const session of response.data.sessions) {
        const sessionStatus =
          session.status === "completed" ? "active" : "inactive";

        yield put(
          updateSessionMeta({
            sessionId: session.session_id,
            meta: {
              status: sessionStatus,
              expiryDate: session.expiryDate,
            },
          })
        );
      }
    } else {
      yield put(getBatchStatusFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error || "Failed to fetch batch status"
      );
    }
  } catch (err) {
    yield put(getBatchStatusFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Failed to fetch batch status"
    );
  }
}
function* getColumnDescriptionsSaga(action) {
  const data = {
    page: 1,
    size: 100,
    file: action?.payload?.file || "",
  };
  try {
    const response = yield call(getColumnDescriptionsApi, data);

    if (response.status === "success") {
      const currentData = yield select(
        (state) => state.config.columnDescriptions
      );
      if (!fastIsEqual(currentData.data, response.data)) {
        yield put(getColumnDescriptionsSuccess(response.data));
      }
      // yield call(
      //   dispatchSuccessToast,
      //   "Column descriptions fetched successfully!"
      // );
    } else {
      yield put(getColumnDescriptionsFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error || "Failed to fetch column descriptions"
      );
    }
  } catch (err) {
    yield put(getColumnDescriptionsFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Failed to fetch column descriptions"
    );
  }
}

function* getClusteringSetsSaga() {
  try {
    const data = { page: 1, size: 100 };
    const response = yield call(getClusteringSetsApi, data);

    if (response.status === "success") {
      yield put(getClusteringSetsSuccess(response.data));
      yield call(dispatchSuccessToast, "Clustering fetched successfully!");
    } else {
      yield put(getClusteringSetsFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error || "Failed to fetch clustering sets"
      );
    }
  } catch (err) {
    yield put(getClusteringSetsFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Failed to fetch clustering sets"
    );
  }
}

// --- watchers ---
export function* watchInitAnalysisSaga() {
  yield takeEvery(initAnalysis, initAnalysisSaga);
}

export function* watchGetRunStatusSaga() {
  yield takeEvery(getRunStatus, getRunStatusSaga);
}
export function* watchGetValidProteomeIdsSaga() {
  yield takeEvery(getValidProteomeIds, getValidProteomeIdsSaga);
}
export function* watchGetColumnDescriptionsSaga() {
  yield takeEvery(getColumnDescriptions, getColumnDescriptionsSaga);
}
export function* watchGetBatchStatusSaga() {
  yield takeEvery(getBatchStatus, getBatchStatusSaga);
}
export function* watchGetClusteringSetsSaga() {
  yield takeEvery(getClusteringSets, getClusteringSetsSaga);
}

// --- root saga ---
export default function* configSaga() {
  yield all([
    fork(watchInitAnalysisSaga),
    fork(watchGetRunStatusSaga),
    fork(watchGetValidProteomeIdsSaga),
    fork(watchGetBatchStatusSaga),
    fork(watchGetClusteringSetsSaga),
    fork(watchGetColumnDescriptionsSaga),
  ]);
}
