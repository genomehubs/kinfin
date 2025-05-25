import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import Modal from "./index";

describe("Modal Component", () => {
  const modalTitle = "Test Modal";
  const modalContent = "This is modal content";

  it("should not render when isOpen is false", () => {
    const { container } = render(
      <Modal isOpen={false} onClose={() => {}}>
        <p>{modalContent}</p>
      </Modal>
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("should render title and content when open", () => {
    render(
      <Modal isOpen={true} onClose={() => {}} title={modalTitle}>
        <p>{modalContent}</p>
      </Modal>
    );

    expect(screen.getByText(modalTitle)).toBeInTheDocument();
    expect(screen.getByText(modalContent)).toBeInTheDocument();
  });

  it("should call onClose when overlay is clicked", () => {
    const onCloseMock = jest.fn();

    render(
      <Modal isOpen={true} onClose={onCloseMock} title={modalTitle}>
        <p>{modalContent}</p>
      </Modal>
    );

    fireEvent.click(screen.getByTestId("modal-overlay"));
    expect(onCloseMock).toHaveBeenCalled();
  });

  it("should call onClose when close icon is clicked", () => {
    const onCloseMock = jest.fn();

    render(
      <Modal isOpen={true} onClose={onCloseMock} title={modalTitle}>
        <p>{modalContent}</p>
      </Modal>
    );

    fireEvent.click(screen.getByRole("button", { name: /close modal/i }));
    expect(onCloseMock).toHaveBeenCalled();
  });

  it("should not render close button if noClose is true", () => {
    render(
      <Modal isOpen={true} onClose={() => {}} noClose={true} title={modalTitle}>
        <p>{modalContent}</p>
      </Modal>
    );

    const closeButton =
      screen.queryByRole("button") ||
      screen.queryByText((_, element) => {
        return (
          element?.tagName.toLowerCase() === "p" &&
          element?.className.includes("closeButton")
        );
      });

    expect(closeButton).toBeNull();
  });
});
