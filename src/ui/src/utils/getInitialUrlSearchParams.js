export function getInitialUrlSearchParams() {
  try {
    if (typeof window === "undefined" || !window.location) {
      return new URLSearchParams();
    }
    return new URLSearchParams(window.location.search || "");
  } catch (err) {
    return new URLSearchParams();
  }
}
