import { useEffect, useRef, useState, useCallback } from "react";

export default function useCarousel({
  length = 1,
  interval = 5000,
  transitionMs = 500,
} = {}) {
  const [current, setCurrent] = useState(0);
  const [isFading, setIsFading] = useState(false);
  const intervalRef = useRef(null);
  const timeoutRef = useRef(null);

  const clearTimers = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (length <= 1) return undefined;

    intervalRef.current = setInterval(() => {
      setIsFading(true);
      timeoutRef.current = setTimeout(() => {
        setCurrent((prev) => (prev + 1) % length);
        setIsFading(false);
      }, transitionMs);
    }, interval);

    return () => {
      clearTimers();
    };
  }, [length, interval, transitionMs, clearTimers]);

  // manual controls
  const goTo = useCallback(
    (index) => {
      clearTimers();
      setIsFading(true);
      timeoutRef.current = setTimeout(() => {
        setCurrent(((index % length) + length) % length);
        setIsFading(false);
      }, transitionMs);
    },
    [clearTimers, length, transitionMs],
  );

  const stop = useCallback(() => {
    clearTimers();
  }, [clearTimers]);

  const start = useCallback(() => {
    clearTimers();
    intervalRef.current = setInterval(() => {
      setIsFading(true);
      timeoutRef.current = setTimeout(() => {
        setCurrent((prev) => (prev + 1) % length);
        setIsFading(false);
      }, transitionMs);
    }, interval);
  }, [clearTimers, interval, length, transitionMs]);

  return {
    current,
    isFading,
    goTo,
    stop,
    start,
  };
}
