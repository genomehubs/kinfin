import React from "react";
import ChartCard from "#components/ChartCard";
import styles from "./Dashboard.module.scss";

const DashboardGrid = ({
  mainCharts,
  rowCharts,
  renderDashboardChart,
  handleDownload,
  handleNavigate,
  downloadLoading,
  rarefactionCurveBlob,
  clusterSizeDistributionBlob,
  selectedAttributeTaxonsetLocal,
  dispatch,
}) => (
  <>
    {mainCharts.map((desc) => (
      <React.Fragment key={desc.key}>
        <ChartCard
          title={desc.title}
          isDownloading={downloadLoading?.[desc.chartKey]}
          onDownload={() =>
            handleDownload({
              chartKey: desc.chartKey,
              dispatch,
              selectedAttributeTaxonset: selectedAttributeTaxonsetLocal,
            })
          }
          onOpen={() => handleNavigate(desc.chartKey)}
        >
          {renderDashboardChart(desc.chartKey)}
        </ChartCard>
      </React.Fragment>
    ))}

    <div className={styles.rowContainer}>
      {rowCharts.map((desc) => {
        const blob =
          desc.chartKey === "rarefactionCurve"
            ? rarefactionCurveBlob
            : desc.chartKey === "clusterSizeDistribution"
              ? clusterSizeDistributionBlob
              : null;
        return (
          <ChartCard
            key={desc.key}
            title={desc.title}
            isDownloading={downloadLoading?.[desc.chartKey]}
            onDownload={() =>
              handleDownload({
                chartKey: desc.chartKey,
                dispatch,
                selectedAttributeTaxonset: selectedAttributeTaxonsetLocal,
                blob,
              })
            }
            onOpen={() => handleNavigate(desc.chartKey)}
            widthPercent={desc.widthPercent}
          >
            {renderDashboardChart(desc.chartKey)}
          </ChartCard>
        );
      })}
    </div>
  </>
);

export default DashboardGrid;
