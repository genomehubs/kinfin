import React, { useRef } from "react";
import { render } from "@testing-library/react";
import { act } from "react";
import useFullscreen from "#hooks/useFullscreen";

function TestComp() {
  const ref = useRef(null);
  const { isFullScreen, enterFullScreen, exitFullScreen } = useFullscreen(ref);
  return (
    <div>
      <div
        ref={ref}
        data-testid="target"
        data-full={isFullScreen ? "1" : "0"}
      />
      <button data-testid="enter" onClick={enterFullScreen} />
      <button data-testid="exit" onClick={exitFullScreen} />
    </div>
  );
}

describe("useFullscreen", () => {
  beforeEach(() => {
    document.exitFullscreen = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  test("enterFullScreen calls element.requestFullscreen and reacts to fullscreenchange", () => {
    const { getByTestId } = render(<TestComp />);
    const target = getByTestId("target");
    // attach a mock requestFullscreen to the DOM node
    target.requestFullscreen = jest.fn();

    act(() => {
      getByTestId("enter").dispatchEvent(
        new MouseEvent("click", { bubbles: true }),
      );
    });

    expect(target.requestFullscreen).toHaveBeenCalled();

    // simulate entering fullscreen
    act(() => {
      // set the global fullscreenElement
      // some environments may not allow assigning, so use Object.defineProperty
      try {
        document.fullscreenElement = target;
      } catch (e) {
        Object.defineProperty(document, "fullscreenElement", {
          configurable: true,
          writable: true,
          value: target,
        });
      }
      document.dispatchEvent(new Event("fullscreenchange"));
    });

    expect(getByTestId("target").dataset.full).toBe("1");

    act(() => {
      getByTestId("exit").dispatchEvent(
        new MouseEvent("click", { bubbles: true }),
      );
    });

    expect(document.exitFullscreen).toHaveBeenCalled();
  });
});
