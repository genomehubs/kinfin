import { useCallback, useEffect, useState } from "react";

export default function useFullscreen(ref) {
  const hasDocument = typeof document !== "undefined";
  const [isFullScreen, setIsFullScreen] = useState(
    hasDocument ? document.fullscreenElement != null : false,
  );

  useEffect(() => {
    if (!hasDocument) return undefined;
    const handler = () => setIsFullScreen(document.fullscreenElement != null);
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, [hasDocument]);

  const enterFullScreen = useCallback(() => {
    const el = ref && ref.current ? ref.current : document.documentElement;
    if (el && el.requestFullscreen) {
      el.requestFullscreen();
    }
  }, [ref]);

  const exitFullScreen = useCallback(() => {
    if (hasDocument && document.exitFullscreen) {
      document.exitFullscreen();
    }
  }, [hasDocument]);

  const toggleFullScreen = useCallback(() => {
    if (!hasDocument) return;
    if (document.fullscreenElement) {
      exitFullScreen();
    } else {
      enterFullScreen();
    }
  }, [hasDocument, enterFullScreen, exitFullScreen]);

  return { isFullScreen, enterFullScreen, exitFullScreen, toggleFullScreen };
}
