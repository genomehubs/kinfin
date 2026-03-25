import React from "react";
import { render, fireEvent } from "@testing-library/react";
import useNavigateBack from "#hooks/useNavigateBack";

jest.mock("react-router-dom", () => ({
  useNavigate: jest.fn(),
}));

function TestComp() {
  const goBack = useNavigateBack();
  return <button data-testid="btn" onClick={goBack} />;
}

describe("useNavigateBack", () => {
  afterEach(() => {
    jest.resetAllMocks();
    // restore history.back if replaced
    if (window.history && window.history.back && window.history.back._isMock) {
      window.history.back = () => {};
    }
  });

  test("calls router navigate(-1) when available", () => {
    const mockNavigate = jest.fn();
    const rr = require("react-router-dom");
    rr.useNavigate.mockReturnValue(mockNavigate);

    const { getByTestId } = render(<TestComp />);
    fireEvent.click(getByTestId("btn"));

    expect(mockNavigate).toHaveBeenCalledWith(-1);
  });

  test("falls back to window.history.back when navigate throws", () => {
    const mockNavigate = jest.fn(() => {
      throw new Error("no router");
    });
    const rr = require("react-router-dom");
    rr.useNavigate.mockReturnValue(mockNavigate);

    const original = window.history.back;
    const mockBack = jest.fn();
    mockBack._isMock = true;
    window.history.back = mockBack;

    const { getByTestId } = render(<TestComp />);
    fireEvent.click(getByTestId("btn"));

    expect(mockBack).toHaveBeenCalled();

    // restore
    window.history.back = original;
  });
});
