import { dispatchSuccessToast } from "./toastNotifications";
import { downloadBlobFile } from "./downloadBlobFile";
import { mapChartName } from "./mappings";
import { setDownloadLoading } from "../app/store/config/slices/uiStateSlice";

/**
 * RTK Query migration: Download handlers now work with blob data directly.
 *
 * With RTK Query, components fetch the blob data using HOCs or hooks (e.g., useGetClusterSummaryQuery).
 * This handler receives the blob data and handles the download.
 *
 * Example usage in a component:
 *   const { clusterSummary, clusterSummaryLoading } = props; // from withClusterSummary HOC
 *   const handleClick = () => {
 *     handleDownload({
 *       chartKey: "clusterSummary",
 *       blob: clusterSummary,
 *       filename: "cluster_summary.tsv"
 *     });
 *   };
 */
const handleDownload = ({ chartKey, blob, filename, dispatch }) => {
  // Fallback for older code that passes dispatch (for UI state updates like loading)
  const showLoading = dispatch
    ? (loading) => dispatch(setDownloadLoading({ type: chartKey, loading }))
    : () => {};

  if (!blob || !(blob instanceof Blob)) {
    console.warn(`No blob data available for ${chartKey}`);
    return;
  }

  showLoading(true);
  dispatchSuccessToast(`${mapChartName(chartKey)} download has started`);

  try {
    downloadBlobFile(blob, filename, blob.type || "application/octet-stream");
  } catch (err) {
    console.error(`Error downloading ${chartKey}:`, err);
  } finally {
    showLoading(false);
  }
};

export { handleDownload };
