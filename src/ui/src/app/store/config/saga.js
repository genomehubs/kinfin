import { takeEvery, fork, put, all, call } from "redux-saga/effects";

import { INIT_ANALYSIS, GET_RUN_STATUS } from "./actionTypes";
import {
  initAnalysisSuccess,
  initAnalysisFailure,
  getRunStatusSuccess,
  getRunStatusFailure,
  storeConfig,
} from "./actions";
import {
  dispatchErrorToast,
  dispatchSuccessToast,
} from "../../../utilis/tostNotifications";
import { initAnalysis, getStatus } from "../../services/client";

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

export function* watchInitAnalysisSaga() {
  yield takeEvery(INIT_ANALYSIS, initAnalysisSaga);
}
export function* watchGetRunStatusSaga() {
  yield takeEvery(GET_RUN_STATUS, getRunStatusSaga);
}

function* configSaga() {
  yield all([fork(watchInitAnalysisSaga), fork(watchGetRunStatusSaga)]);
}

export default configSaga;
