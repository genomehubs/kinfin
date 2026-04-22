import React from "react";
import ChartCard from "#components/ChartCard";

const DashboardChart = ({
  chartKey,
  title,
  isDownloading,
  onOpen,
  onDownload,
  widthPercent,
  renderChart,
}) => {
  return (
    <ChartCard
      title={title}
      isDownloading={isDownloading}
      onDownload={onDownload}
      onOpen={onOpen}
      widthPercent={widthPercent}
    >
      {renderChart && renderChart()}
    </ChartCard>
  );
};

export default DashboardChart;
