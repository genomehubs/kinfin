import { applyMiddleware, compose, createStore } from "redux";
import { persistReducer, persistStore } from "redux-persist";
import createSagaMiddleware from "redux-saga";
import createIndexedDBStorage from "redux-persist-indexeddb-storage"; // Import IndexedDB storage
import rootReducer from "./reducers";
import rootSaga from "./sagas";

// Use IndexedDB storage
const storage = createIndexedDBStorage("myReduxDB");

const persistConfig = {
  key: "root",
  storage, // Use IndexedDB
  blacklist: ["customerAuth"], // Do not persist customerAuth
};

const persistedReducer = persistReducer(persistConfig, rootReducer);

const sagaMiddleware = createSagaMiddleware();

const composeEnhancers =
  (typeof window !== "undefined" &&
    window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__) ||
  compose;

const store = createStore(
  persistedReducer,
  {},
  composeEnhancers(applyMiddleware(sagaMiddleware))
);

const persistor = persistStore(store);

sagaMiddleware.run(rootSaga);

export { persistor, store };
