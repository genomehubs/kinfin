import { configureStore } from "@reduxjs/toolkit";
import { persistReducer, persistStore } from "redux-persist";
import createSagaMiddleware from "redux-saga";
import createIndexedDBStorage from "redux-persist-indexeddb-storage";
import rootReducer from "./reducers";
import rootSaga from "./sagas";

const storage = createIndexedDBStorage("myReduxDB");

const persistConfig = {
  key: "root",
  storage,
};

const persistedReducer = persistReducer(persistConfig, rootReducer);

const sagaMiddleware = createSagaMiddleware();

const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      thunk: false,
      serializableCheck: false,
      immutableCheck: false,
    }).concat(sagaMiddleware),
  devTools: process.env.NODE_ENV !== "production",
});

const persistor = persistStore(store);

sagaMiddleware.run(rootSaga);

export { persistor, store };
