import React from "react";
import { action } from "@storybook/addon-actions";
import TableComponent from "./index";

export default {
  title: "Components/TableComponent",
  component: TableComponent,
  argTypes: {
    loading: { control: "boolean" },
    onRowClick: { action: "row clicked" },
    // We disable controls for columns/data since they’re complex objects
    columns: { table: { disable: true } },
    data: { table: { disable: true } },
    className: { control: "text" },
  },
};

// Sample columns definition
const sampleColumns = [
  {
    Header: "First Name",
    accessor: "firstName",
    sortable: true,
  },
  {
    Header: "Last Name",
    accessor: "lastName",
    sortable: true,
  },
  {
    Header: "Age",
    accessor: "age",
    sortable: true,
  },
];

// Sample data array
const sampleData = [
  { firstName: "Alice", lastName: "Johnson", age: 28 },
  { firstName: "Bob", lastName: "Smith", age: 34 },
  { firstName: "Carol", lastName: "Lee", age: 22 },
  { firstName: "David", lastName: "Kim", age: 45 },
];

const Template = (args) => <TableComponent {...args} />;

export const Default = Template.bind({});
Default.args = {
  columns: sampleColumns,
  data: sampleData,
  loading: false,
  onRowClick: action("row clicked"),
  className: "",
};

export const Loading = Template.bind({});
Loading.args = {
  columns: sampleColumns,
  data: [], // data ignored when loading=true
  loading: true,
  onRowClick: action("row clicked"),
  className: "",
};

export const NoData = Template.bind({});
NoData.args = {
  columns: sampleColumns,
  data: [], // triggers “No data Found” state
  loading: false,
  onRowClick: action("row clicked"),
  className: "",
};
