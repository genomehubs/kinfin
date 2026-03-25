import React from "react";
import { render } from "@testing-library/react";
import useIsCurrentPage from "#hooks/useIsCurrentPage";

jest.mock("react-router-dom", () => ({
  useLocation: jest.fn(),
}));

function TestComp({ fragment }) {
  const val = useIsCurrentPage(fragment);
  return <div data-testid="val">{val ? "1" : "0"}</div>;
}

describe("useIsCurrentPage", () => {
  afterEach(() => jest.resetAllMocks());

  test("returns true when pathname includes fragment", () => {
    const rr = require("react-router-dom");
    rr.useLocation.mockReturnValue({ pathname: "/foo/bar" });

    const { getByTestId } = render(<TestComp fragment="foo" />);
    expect(getByTestId("val").textContent).toBe("1");
  });

  test("returns false when pathname does not include fragment", () => {
    const rr = require("react-router-dom");
    rr.useLocation.mockReturnValue({ pathname: "/foo/bar" });

    const { getByTestId } = render(<TestComp fragment="baz" />);
    expect(getByTestId("val").textContent).toBe("0");
  });

  test("returns false when fragment is falsy", () => {
    const rr = require("react-router-dom");
    rr.useLocation.mockReturnValue({ pathname: "/foo/bar" });

    const { getByTestId } = render(<TestComp />);
    expect(getByTestId("val").textContent).toBe("0");
  });
});
