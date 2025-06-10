import { combineReducers } from "redux";
import analysisReducer from "./analysis/reducers";
import configReducer from "./config/reducers";

const rootReducer = combineReducers({
  analysis: analysisReducer,
  config: configReducer,
});

export default rootReducer;
