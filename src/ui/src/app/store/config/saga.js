import { takeEvery, fork, put, all, call, delay } from "redux-saga/effects";
import { INIT_ANALYSIS, GET_RUN_STATUS, GET_BATCH_STATUS } from "./actionTypes";

import {
  initAnalysisSuccess,
  initAnalysisFailure,
  getRunStatusSuccess,
  getRunStatusFailure,
  storeConfig,
  setPollingLoading,
  getBatchStatusSuccess,
  getBatchStatusFailure,
  updateSessionMeta,
} from "./actions";

import {
  dispatchErrorToast,
  dispatchSuccessToast,
} from "../../../utilis/tostNotifications";

import { initAnalysis, getStatus, getBatchStatus } from "../../services/client";

const POLLING_INTERVAL = 5000; // 5 seconds
const MAX_POLLING_ATTEMPTS = 120; // 10 minutes

function* pollRunStatusSaga(sessionId, navigate) {
  yield put(setPollingLoading(true));
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
          yield call(navigate, `/${sessionId}/dashboard`);
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
    yield put(setPollingLoading(false));
  }
}

function* initAnalysisSaga(action) {
  const { name, config, navigate } = action.payload;
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
      yield call(
        dispatchSuccessToast,
        "KinFin analysis has started. Please wait..."
      );
      yield fork(pollRunStatusSaga, response.data.session_id, navigate); // start polling
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
export function* getBatchStatusSaga(action) {
  const { sessionIds } = action.payload;
  try {
    const response = yield call(getBatchStatus, sessionIds);
    if (response.status === "success") {
      yield put(getBatchStatusSuccess(response.data));
      yield call(dispatchSuccessToast, "Batch status fetched successfully!");
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

export function* watchInitAnalysisSaga() {
  yield takeEvery(INIT_ANALYSIS, initAnalysisSaga);
}
export function* watchGetRunStatusSaga() {
  yield takeEvery(GET_RUN_STATUS, getRunStatusSaga);
}
export function* watchGetBatchStatusSaga() {
  yield takeEvery(GET_BATCH_STATUS, getBatchStatusSaga);
}

export default function* configSaga() {
  yield all([
    fork(watchInitAnalysisSaga),
    fork(watchGetRunStatusSaga),
    fork(watchGetBatchStatusSaga),
  ]);
}
