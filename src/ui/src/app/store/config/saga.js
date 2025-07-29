import {
  takeEvery,
  fork,
  put,
  all,
  call,
  delay,
  select,
} from "redux-saga/effects";
import {
  INIT_ANALYSIS,
  GET_RUN_STATUS,
  GET_BATCH_STATUS,
  GET_VALID_PROTEOME_IDS,
  GET_CLUSTERING_SETS,
  GET_COLUMN_DESCRIPTIONS,
} from "./actionTypes";

import {
  initAnalysisSuccess,
  initAnalysisFailure,
  getRunStatusSuccess,
  getRunStatusFailure,
  storeConfig,
  getValidProteomeIdsSuccess,
  getValidProteomeIdsFailure,
  setPollingLoading,
  getBatchStatusSuccess,
  getBatchStatusFailure,
  updateSessionMeta,
  getClusteringSetsFailure,
  getClusteringSetsSuccess,
  getColumnDescriptionsSuccess,
  getColumnDescriptionsFailure,
} from "./actions";

import {
  dispatchErrorToast,
  dispatchSuccessToast,
} from "../../../utilis/tostNotifications";

import {
  initAnalysis,
  getStatus,
  getBatchStatus,
  getValidProteomeIds,
  getClusteringSets,
  getColumnDescriptions,
} from "../../services/client";

const POLLING_INTERVAL = 5000; // 5 seconds
const MAX_POLLING_ATTEMPTS = 120; // 10 minutes

const selectSessionStatusById = (session_id) => (state) => {
  return state?.config?.storeConfig?.data?.[session_id]?.status;
};

const getSessionId = () =>
  localStorage.getItem("currentSessionId") ||
  "6599179a64accf331ffe653db00a0e24";

function* pollRunStatusSaga(sessionId) {
  yield put(setPollingLoading({ sessionId, loading: true }));
  try {
    let isComplete = false;
    let attempts = 0;

    while (!isComplete && attempts < MAX_POLLING_ATTEMPTS) {
      const response = yield call(getStatus, sessionId);

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
  const data = {
    config: config,
    clusterId: clusterId,
  };
  try {
    const response = yield call(initAnalysis, data);
    if (response.status === "success") {
      yield put(initAnalysisSuccess(response.data));
      const payloadForIndexDBStorage = {
        name,
        config,
        sessionId: response.data.session_id,
        clusterId: clusterId,
        clusterName: clusterName,
      };
      yield put(storeConfig(payloadForIndexDBStorage));
      yield call(navigate, `/${response.data.session_id}/dashboard`);
      yield fork(pollRunStatusSaga, response.data.session_id); // start polling
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
    const status = yield select(selectSessionStatusById(getSessionId()));

    if (!status) {
      return;
    }
    const response = yield call(getStatus);
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
    const data = {
      page: 1,
      size: 100,
      clusterId: clusterId,
    };
    const response = yield call(getValidProteomeIds, data);

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
    const response = yield call(getBatchStatus, sessionIds);
    if (response.status === "success") {
      yield put(getBatchStatusSuccess(response.data));

      for (const session of response.data.sessions) {
        const isActive = session.status === "completed";

        yield put(
          updateSessionMeta(session.session_id, {
            status: isActive,
            expiryDate: session.expiryDate,
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

function* getClusteringSetsSaga() {
  try {
    const data = {
      page: 1,
      size: 100,
    };
    const response = yield call(getClusteringSets, data);

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
    yield put(getValidProteomeIdsFailure(err));
    yield call(
      dispatchErrorToast,
      err?.response?.data?.error || "Failed to fetch clustering sets"
    );
  }
}

function* getColumnDescriptionsSaga(action) {
  console.log("first");
  const data = {
    page: 1,
    size: 100,
  };
  try {
    const response = yield call(getColumnDescriptions, data);
    console.log("🚀 ~ getColumnDescriptionsSaga ~ response:", response);

    if (response.status === "success") {
      yield put(getColumnDescriptionsSuccess(response.data));
      yield call(
        dispatchSuccessToast,
        "Column descriptions fetched successfully!"
      );
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

export function* watchInitAnalysisSaga() {
  yield takeEvery(INIT_ANALYSIS, initAnalysisSaga);
}

export function* watchGetColumnDescriptionsSaga() {
  yield takeEvery(GET_COLUMN_DESCRIPTIONS, getColumnDescriptionsSaga);
}
export function* watchGetRunStatusSaga() {
  yield takeEvery(GET_RUN_STATUS, getRunStatusSaga);
}
export function* watchGetValidProteomeIdsSaga() {
  yield takeEvery(GET_VALID_PROTEOME_IDS, getValidProteomeIdsSaga);
}
export function* watchGetBatchStatusSaga() {
  yield takeEvery(GET_BATCH_STATUS, getBatchStatusSaga);
}

export function* watchGetClusteringSets() {
  yield takeEvery(GET_CLUSTERING_SETS, getClusteringSetsSaga);
}

export default function* configSaga() {
  yield all([
    fork(watchInitAnalysisSaga),

    fork(watchGetRunStatusSaga),
    fork(watchGetValidProteomeIdsSaga),
    fork(watchGetBatchStatusSaga),
    fork(watchGetClusteringSets),
    fork(watchGetColumnDescriptionsSaga),
  ]);
}
