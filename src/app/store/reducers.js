import { combineReducers } from "redux";
import analysisReducer from "./kinfin/reducers";

const rootReducer = combineReducers({
  analysis: analysisReducer,
});

export default rootReducer;
