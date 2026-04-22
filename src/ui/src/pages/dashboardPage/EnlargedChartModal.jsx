import React from "react";
import Modal from "@mui/material/Modal";
import Box from "@mui/material/Box";
import { mapChartName } from "../../utils/mappings";
import AttributeSummary from "#components/Charts/AttributeSummary";
import ClusterSummary from "#components/Charts/ClusterSummary";
import ClusterMetrics from "#components/Charts/ClusterMetrics";

const EnlargedChartModal = ({
  enlargedChart,
  open,
  onClose,
  selectedAttributeTaxonsetLocal,
  attributeSummary,
  clusterSummary,
  clusterMetrics,
}) => {
  const renderContent = () => {
    switch (enlargedChart) {
      case "attributeSummary":
        return (
          <AttributeSummary
            attribute={selectedAttributeTaxonsetLocal.attribute}
            attributeSummaryColumnDescriptions={attributeSummary}
          />
        );
      case "clusterSummary":
        return (
          <ClusterSummary
            attribute={selectedAttributeTaxonsetLocal.attribute}
            clusterSummaryColumnDescriptions={clusterSummary}
          />
        );
      case "clusterMetrics":
        return (
          <ClusterMetrics
            attribute={selectedAttributeTaxonsetLocal.attribute}
            taxonset={selectedAttributeTaxonsetLocal.taxonset}
            clusterMetricsColumnDescriptions={clusterMetrics}
          />
        );
      default:
        return null;
    }
  };

  return (
    <Modal open={!!open} onClose={onClose}>
      <Box
        sx={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: "90%",
          maxWidth: 1000,
          maxHeight: "90vh",
          bgcolor: "var(--bg-color)",
          color: "var(--text-color)",
          boxShadow: 24,
          p: 4,
          overflowY: "auto",
          borderRadius: 2,
        }}
      >
        <h2>{mapChartName(enlargedChart)}</h2>
        <div>{renderContent()}</div>
      </Box>
    </Modal>
  );
};

export default EnlargedChartModal;
