import React from "react";
import ChartCard from "../../components/ChartCard";
import CustomisationDialog from "../../components/CustomisationDialog";

export default function BaseChartPage({
  title,
  isDownloading,
  onDownload,
  onCustomise,
  onClose,
  customiseProps,
  children,
}) {
  return (
    <>
      <div>
        <ChartCard
          title={title}
          isDownloading={isDownloading}
          onDownload={onDownload}
          onCustomise={onCustomise}
          onClose={onClose}
        >
          {children}
        </ChartCard>
      </div>

      {customiseProps ? (
        <CustomisationDialog
          open={customiseProps.open}
          onClose={customiseProps.onClose}
          onApply={customiseProps.onApply}
          selectedCodes={customiseProps.selectedCodes}
          columnDescriptions={customiseProps.columnDescriptions}
          title={customiseProps.title}
        />
      ) : null}
    </>
  );
}
