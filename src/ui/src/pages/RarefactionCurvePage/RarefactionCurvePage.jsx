import React from "react";
import { useSelector } from "react-redux";
import ChartPageShell from "#components/ChartPageShell";
import RarefactionCurve from "#components/Charts/RarefactionCurve";

const RarefactionCurvePage = ({
  rarefactionCurveBlob,
  attribute: propAttribute,
  taxonset: propTaxonset,
  setSelectedAttributeTaxonset: propSetSelectedAttributeTaxonset,
}) => {
  const downloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading,
  );

  const isDownloading = downloadLoading?.downloadLoading?.rarefactionCurve;

  return (
    <ChartPageShell
      title="Rarefaction Curve"
      chartKey="rarefaction-curve"
      searchParamKey={null}
      isDownloading={isDownloading}
      initialAttribute={propAttribute}
      initialTaxonset={propTaxonset}
      setSelectedAttributeTaxonsetProp={propSetSelectedAttributeTaxonset}
      blob={rarefactionCurveBlob}
      renderChart={({ attribute }) => (
        <RarefactionCurve attribute={attribute} />
      )}
    />
  );
};

export default RarefactionCurvePage;
