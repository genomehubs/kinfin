import React from "react";
import { render, waitFor } from "@testing-library/react";

// Mock the RTK Query hook
jest.mock("#store/api", () => ({
  useGetRunStatusQuery: jest.fn(),
}));

// We don't need to mock the action creators; inspect dispatched actions instead

// Mock useDispatch
const mockDispatch = jest.fn();
jest.mock("react-redux", () => ({
  useDispatch: () => mockDispatch,
}));

import useSessionPolling from "#hooks/useSessionPolling";
import { useGetRunStatusQuery } from "#store/api";

function TestComp({ sessionId }) {
  useSessionPolling(sessionId);
  return <div />;
}

describe("useSessionPolling", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("dispatches storeConfig and setPollingLoading for completed session", async () => {
    const meta = {
      data: { status: "completed", isComplete: true, name: "S1" },
    };
    useGetRunStatusQuery.mockReturnValue({ data: meta, isLoading: false });

    const { rerender } = render(<TestComp sessionId="s1" />);

    await waitFor(() => {
      expect(mockDispatch).toHaveBeenCalled();
    });

    // first call should be storeConfig action
    const first = mockDispatch.mock.calls[0][0];
    expect(first.type).toMatch(/storeConfig$/);
    expect(first.payload.sessionId).toBe("s1");
    expect(first.payload.meta.status).toBe("active");

    // second call should be setPollingLoading with loading false
    const second = mockDispatch.mock.calls[1][0];
    expect(second.type).toMatch(/setPollingLoading$/i);
    expect(second.payload.loading).toBe(false);

    // change to running -> should set loading true and keep polling
    const runningMeta = {
      data: { status: "running", isComplete: false, name: "S1" },
    };
    useGetRunStatusQuery.mockReturnValue({
      data: runningMeta,
      isLoading: false,
    });
    rerender(<TestComp sessionId="s1" />);

    await waitFor(() => {
      // called at least 3 times now
      expect(mockDispatch.mock.calls.length).toBeGreaterThanOrEqual(3);
    });

    const last = mockDispatch.mock.calls[mockDispatch.mock.calls.length - 1][0];
    expect(last.type).toMatch(/setPollingLoading$/i);
    expect(last.payload.loading).toBe(true);
  });

  test("does not dispatch when no sessionId is provided", async () => {
    useGetRunStatusQuery.mockReturnValue({ data: null, isLoading: false });
    render(<TestComp sessionId={null} />);
    // give effects a tick
    await waitFor(() => {
      expect(mockDispatch).not.toHaveBeenCalled();
    });
  });

  test("handles dispatch throwing without crashing and recovers", async () => {
    // make dispatch throw on first call
    const throwing = jest.fn(() => {
      throw new Error("dispatch fail");
    });
    mockDispatch.mockImplementationOnce(throwing);

    const meta = {
      data: { status: "completed", isComplete: true, name: "S2" },
    };
    useGetRunStatusQuery.mockReturnValue({ data: meta, isLoading: false });

    const { rerender } = render(<TestComp sessionId="s2" />);

    // despite dispatch throwing, component should not throw
    await waitFor(() => {
      expect(throwing).toHaveBeenCalled();
    });

    // now make dispatch behave normally and send an updated meta
    mockDispatch.mockClear();
    const meta2 = {
      data: { status: "running", isComplete: false, name: "S2" },
    };
    useGetRunStatusQuery.mockReturnValue({ data: meta2, isLoading: false });
    rerender(<TestComp sessionId="s2" />);

    await waitFor(() => {
      expect(mockDispatch).toHaveBeenCalled();
    });
  });
});
