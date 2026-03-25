const SESSION_KEY = "currentSessionId";

export function getSessionId() {
  try {
    return (
      localStorage.getItem(SESSION_KEY) || "6599179a64accf331ffe653db00a0e24"
    );
  } catch (err) {
    // In environments without localStorage (tests/SSR), fail gracefully
    return null;
  }
}

export function setSessionId(sessionId) {
  try {
    if (sessionId) localStorage.setItem(SESSION_KEY, sessionId);
  } catch (err) {
    // noop
  }
}

export function clearSessionId() {
  try {
    localStorage.removeItem(SESSION_KEY);
  } catch (err) {
    // noop
  }
}

export default {
  getSessionId,
  setSessionId,
  clearSessionId,
};
