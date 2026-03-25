import React from "react";
import { render } from "@testing-library/react";
import { act } from "react";
import useCarousel from "#hooks/useCarousel";

jest.useFakeTimers();

afterEach(() => {
  jest.clearAllTimers();
});

function TestComp({ length, interval, transitionMs }) {
  const { current, isFading } = useCarousel({
    length,
    interval,
    transitionMs,
  });
  return (
    <div>
      <span data-testid="current">{current}</span>
      <span data-testid="fading">{isFading ? "1" : "0"}</span>
    </div>
  );
}

test("useCarousel advances and sets fading", () => {
  const { getByTestId } = render(
    <TestComp length={3} interval={1000} transitionMs={200} />,
  );

  expect(getByTestId("current").textContent).toBe("0");
  act(() => {
    jest.advanceTimersByTime(1000);
  });

  // during transition fading should be true
  expect(getByTestId("fading").textContent).toBe("1");

  act(() => {
    jest.advanceTimersByTime(200);
  });

  expect(getByTestId("current").textContent).toBe("1");
  expect(getByTestId("fading").textContent).toBe("0");
});
