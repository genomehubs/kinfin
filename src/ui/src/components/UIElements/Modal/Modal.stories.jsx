import React from "react";
import Modal from "./index"; // adjust the path if needed

export default {
  title: "Components/Modal",
  component: Modal,
  argTypes: {
    title: { control: "text" },
    noClose: { control: "boolean" },
    isOpen: { control: "boolean" },
    // children cannot be dynamically controlled via Storybook UI panel
    children: {
      control: false,
    },
  },
};

const Template = (args) => (
  <>
    <button onClick={args.onOpen || (() => {})}>Open Modal</button>
    <Modal {...args} />
  </>
);

export const Default = Template.bind({});
Default.args = {
  title: "Sample Modal",
  noClose: false,
  isOpen: true,
  onClose: () => alert("Modal closed"),
  children: (
    <div>
      <p>
        This is a <strong>sample modal</strong> with <code>JSX</code> content.
      </p>
      <ul>
        <li>Reusable</li>
        <li>Flexible</li>
        <li>Styled</li>
      </ul>
    </div>
  ),
};

export const NoCloseButton = Template.bind({});
NoCloseButton.args = {
  title: "No Close Button Modal",
  noClose: true,
  isOpen: true,
  onClose: () => alert("Modal closed"),
  children: (
    <div>
      <p>You cannot close this modal via the close icon.</p>
    </div>
  ),
};
