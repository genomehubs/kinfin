// toastNotifications.js
import { toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css"; // Import styles

// // Configure Toastify
// toast.configure();

const dispatchSuccessToast = (toastMessage) => {
  toast.success(toastMessage, {
    position: "top-center",
    autoClose: 5000,
    hideProgressBar: true,
    style: {
      background: "#2ecc71",
      color: "#1c1c1c",
      fontSize: "1rem",
    },
  });
};

const dispatchErrorToast = (toastMessage) => {
  toast.error(toastMessage, {
    position: "top-center",
    autoClose: 5000,
    hideProgressBar: true,
    style: {
      background: "#f7cdd2",
      color: "#1c1c1c",
      fontSize: "1rem",
    },
  });
};

export { dispatchSuccessToast, dispatchErrorToast };
