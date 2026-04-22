import React from "react";
import { render, fireEvent } from "@testing-library/react";

// Mock dependencies used by the hook
jest.mock("#hooks/useValidProteomeIds.js", () => ({
  useValidProteomeIds: () => ({ data: {}, isError: false }),
}));

jest.mock("#utils/validateDataset", () => ({
  validateDataset: (data) => ({ data, errors: {} }),
}));

import useFileUpload from "#hooks/useFileUpload";

function TestComp({ file }) {
  const { handleFileChange, parsedData, jsonText, selectedFileName } =
    useFileUpload();

  return (
    <div>
      <button
        data-testid="btn"
        onClick={() =>
          handleFileChange({ target: { files: file ? [file] : [] } })
        }
      />
      <div data-testid="name">{selectedFileName}</div>
      <pre data-testid="parsed">
        {parsedData ? JSON.stringify(parsedData) : ""}
      </pre>
      <pre data-testid="json">{jsonText}</pre>
    </div>
  );
}

describe("useFileUpload", () => {
  let origFileReader;

  beforeEach(() => {
    origFileReader = global.FileReader;

    class MockFileReader {
      constructor() {
        this.onload = null;
        this.result = null;
      }
      readAsText(file) {
        this.result = file.content;
        if (this.onload) this.onload({ target: { result: this.result } });
      }
      readAsArrayBuffer(file) {
        // simulate array buffer result
        const enc = new TextEncoder();
        this.result = enc.encode(file.content || "").buffer;
        if (this.onload) this.onload({ target: { result: this.result } });
      }
    }

    global.FileReader = MockFileReader;
  });

  afterEach(() => {
    global.FileReader = origFileReader;
    jest.resetAllMocks();
  });

  test("parses JSON file and updates parsedData/jsonText", () => {
    const file = { name: "data.json", content: '[{"taxon":"T1","val":"A"}]' };

    const { getByTestId } = render(<TestComp file={file} />);
    fireEvent.click(getByTestId("btn"));

    expect(getByTestId("name").textContent).toBe("data.json");
    expect(getByTestId("parsed").textContent).toBe(
      JSON.stringify([{ taxon: "T1", val: "A" }]),
    );
    const jsonText = getByTestId("json").textContent;
    expect(jsonText).toContain("taxon");
    expect(jsonText).toContain("T1");
  });

  test("parses CSV file and updates parsedData", () => {
    const csv = "taxon,val\nT1,A\nT2,B";
    const file = { name: "data.csv", content: csv };

    const { getByTestId } = render(<TestComp file={file} />);
    fireEvent.click(getByTestId("btn"));

    const parsed = JSON.parse(getByTestId("parsed").textContent);
    expect(Array.isArray(parsed)).toBe(true);
    expect(parsed.length).toBe(2);
    expect(parsed[0].taxon).toBe("T1");
    expect(parsed[0].val).toBe("A");
  });
});
