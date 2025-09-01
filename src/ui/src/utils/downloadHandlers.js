import { dispatchSuccessToast } from "./toastNotifications";
import { downloadBlobFile } from "./downloadBlobFile";
import { getAttributeSummary } from "../app/store/analysis/slices/attributeSummarySlice";
import { getClusterMetrics } from "../app/store/analysis/slices/clusterMetricsSlice";
import { getClusterSummary } from "../app/store/analysis/slices/clusterSummarySlice";
import { mapChartName } from "./mappings";
import { setDownloadLoading } from "../app/store/config/slices/uiStateSlice";

const handleDownload = ({
  chartKey,
  dispatch,
  selectedAttributeTaxonset,
  rarefactionCurveBlob,
  clusterSizeDistributionBlob,
}) => {
  dispatch(setDownloadLoading({ type: chartKey, loading: true }));

  const attribute = selectedAttributeTaxonset?.attribute;
  const taxonSet = selectedAttributeTaxonset?.taxonset;
  const basePayload = {
    attribute,
    taxonSet,
    asFile: true,
  };

  dispatchSuccessToast(`${mapChartName(chartKey)} download has started`);

  switch (chartKey) {
    case "attributeSummary":
      dispatch(getAttributeSummary(basePayload));
      break;
    case "clusterSummary":
      dispatch(getClusterSummary(basePayload));
      break;
    case "clusterMetrics":
      dispatch(getClusterMetrics(basePayload));
      break;
    case "rarefactionCurve":
      if (rarefactionCurveBlob instanceof Blob) {
        downloadBlobFile(
          rarefactionCurveBlob,
          "rarefaction_curve.png",
          "image/png"
        );
        dispatch(setDownloadLoading({ type: chartKey, loading: false }));
      }
      break;
    case "clusterSizeDistribution":
      if (clusterSizeDistributionBlob instanceof Blob) {
        downloadBlobFile(
          clusterSizeDistributionBlob,
          "cluster_size_distribution.png",
          "image/png"
        );
        dispatch(setDownloadLoading({ type: chartKey, loading: false }));
      }
      break;
    default:
      console.warn("Invalid chart key for download:", chartKey);
  }

  setTimeout(() => {
    dispatch(setDownloadLoading({ type: chartKey, loading: false }));
  }, 30000);
};

export { handleDownload };
