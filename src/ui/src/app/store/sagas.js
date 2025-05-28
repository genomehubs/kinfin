import { all } from "redux-saga/effects";

import analysisSaga from "./kinfin/saga";

export default function* rootSaga() {
  yield all([analysisSaga()]);
}
