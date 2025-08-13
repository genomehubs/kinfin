// snackbarNotifications.js
import { enqueueSnackbar } from "notistack";

const dispatchSuccessToast = (message) => {
  enqueueSnackbar(message, {
    variant: "success",
    anchorOrigin: {
      vertical: "bottom",
      horizontal: "left",
    },
    autoHideDuration: 5000,
    style: {
      backgroundColor: "#2ecc71",
      color: "#ffffff",
      fontSize: "1rem",
    },
  });
};

const dispatchErrorToast = (message) => {
  enqueueSnackbar(message, {
    variant: "error",
    anchorOrigin: {
      vertical: "bottom",
      horizontal: "left",
    },
    autoHideDuration: 5000,
    style: {
      backgroundColor: "#f7cdd2",
      color: "#1c1c1c",
      fontSize: "1rem",
    },
  });
};

export { dispatchSuccessToast, dispatchErrorToast };
