import {
  takeEvery,
  fork,
  put,
  all,
  call,
  delay,
  select,
} from "redux-saga/effects";

// --- slice actions ---
import {
  initAnalysis,
  initAnalysisSuccess,
  initAnalysisFailure,
} from "./slices/analysisSlice";

import {
  getRunStatus,
  getRunStatusSuccess,
  getRunStatusFailure,
} from "./slices/runStatusSlice";

import { storeConfig, updateSessionMeta } from "./slices/configSlice";

import {
  getValidProteomeIds,
  getValidProteomeIdsSuccess,
  getValidProteomeIdsFailure,
} from "./slices/proteomeIdsSlice";

import {
  getBatchStatus,
  getBatchStatusSuccess,
  getBatchStatusFailure,
} from "./slices/batchStatusSlice";

import {
  getColumnDescriptions,
  getColumnDescriptionsFailure,
  getColumnDescriptionsSuccess,
} from "./slices/columnDescriptionsSlice";

import {
  getClusteringSets,
  getClusteringSetsSuccess,
  getClusteringSetsFailure,
} from "./slices/clusteringSetsSlice";

import { setPollingLoading } from "./slices/uiStateSlice";

import {
  dispatchErrorToast,
  dispatchSuccessToast,
} from "../../../utils/toastNotifications";

import {
  initAnalysis as initAnalysisApi,
  getStatus as getStatusApi,
  getBatchStatus as getBatchStatusApi,
  getValidProteomeIds as getValidProteomeIdsApi,
  getClusteringSets as getClusteringSetsApi,
  getColumnDescriptions as getColumnDescriptionsApi,
} from "../../services/client";

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
  try {
    const data = { page: 1, size: 100, clusterId };
    const response = yield call(getValidProteomeIdsApi, data);

    if (response.status === "success") {
      yield put(getValidProteomeIdsSuccess(response.data));
    } else {
      yield put(getValidProteomeIdsFailure(response));
      yield call(
        dispatchErrorToast,
        response?.error || "Failed to fetch valid proteome IDs"
      );
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
      yield put(getColumnDescriptionsSuccess(response.data));
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
