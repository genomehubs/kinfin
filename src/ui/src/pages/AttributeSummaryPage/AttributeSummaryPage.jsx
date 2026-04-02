import AttributeSummary from "../../components/Charts/AttributeSummary";
import ChartPageShell from "../../components/ChartPageShell";
import React from "react";
import useColumnDescriptionsSets from "#hooks/useColumnDescriptionsSets.js";

const AttributeSummaryPage = ({
  attribute: propAttribute,
  taxonset: propTaxonset,
  setSelectedAttributeTaxonset: propSetSelectedAttributeTaxonset,
}) => {
  // Use the pre-grouped sets so the page gets only attribute-related columns
  const { attributeSummary: attributeColumns } = useColumnDescriptionsSets();

  return (
    <ChartPageShell
      title="Attribute Summary"
      chartKey="attributeSummary"
      searchParamKey="AS_code"
      columnDescriptions={attributeColumns}
      initialAttribute={propAttribute}
      initialTaxonset={propTaxonset}
      setSelectedAttributeTaxonsetProp={propSetSelectedAttributeTaxonset}
      renderChart={({ attribute, effectiveColumnDescriptions }) => (
        <AttributeSummary
          attribute={attribute}
          attributeSummaryColumnDescriptions={effectiveColumnDescriptions}
        />
      )}
    />
  );
};

export default AttributeSummaryPage;
