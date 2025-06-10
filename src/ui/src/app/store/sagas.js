import { all } from "redux-saga/effects";

import analysisSaga from "./analysis/saga";
import configSaga from "./config/saga";

export default function* rootSaga() {
  yield all([analysisSaga(), configSaga()]);
}
