import React, { useState, useEffect } from "react";
import styles from "./ClusterMetrics.module.scss";
import AppLayout from "../../components/AppLayout";
import ClusterMetrics from "../../components/Charts/ClusterMetrics";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import { useDispatch, useSelector } from "react-redux";
import { getClusterMetrics } from "../../app/store/analysis/actions";
import { dispatchSuccessToast } from "../../utilis/tostNotifications";
import { setDownloadLoading } from "../../app/store/config/actions";
import { useSearchParams } from "react-router-dom";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Checkbox,
  Button,
} from "@mui/material";

const ClusterMetricsPage = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.selectedAttributeTaxonset
  );
  const clusterMetricsDownloadLoading = useSelector(
    (state) => state?.config?.downloadLoading?.clusterMetrics
  );

  const columnDescriptions = useSelector(
    (state) => state?.config?.columnDescriptions?.data || []
  );

  const [customiseOpen, setCustomiseOpen] = useState(false);
  const [selectedCodes, setSelectedCodes] = useState([]);

  useEffect(() => {
    const paramsCodes = searchParams.getAll("CM_code");
    setSelectedCodes(paramsCodes);
  }, [searchParams]);

  // Download handler
  const handleDownload = () => {
    dispatch(setDownloadLoading({ type: "clusterMetrics", loading: true }));
    const payload = {
      attribute: selectedAttributeTaxonset?.attribute,
      taxonSet: selectedAttributeTaxonset?.taxonset,
      asFile: true,
    };
    dispatchSuccessToast("Cluster Metrics download has started");
    dispatch(getClusterMetrics(payload));
    setTimeout(
      () =>
        dispatch(
          setDownloadLoading({ type: "clusterMetrics", loading: false })
        ),
      30000
    );
  };

  // Open customisation modal
  const handleCustomisation = () => {
    setCustomiseOpen(true);
  };

  // Checkbox handler
  const handleCheckboxChange = (code) => {
    setSelectedCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  // Apply customisation
  const handleApply = () => {
    const newParams = new URLSearchParams(searchParams);
    newParams.delete("CM_code");
    selectedCodes.forEach((c) => newParams.append("CM_code", c));
    setSearchParams(newParams);
    setCustomiseOpen(false);
  };

  const handleCancel = () => {
    setCustomiseOpen(false);
  };

  return (
    <AppLayout>
      <div className={styles.pageHeader}>
        <AttributeSelector />
      </div>
      <div className={styles.page}>
        <div className={styles.chartsContainer}>
          <ChartCard
            title="Cluster Metrics"
            isDownloading={clusterMetricsDownloadLoading}
            onDownload={handleDownload}
            onCustomise={handleCustomisation}
          >
            <ClusterMetrics />
          </ChartCard>
        </div>
      </div>

      {/* Customisation Modal */}
      <Dialog
        open={customiseOpen}
        onClose={handleCancel}
        fullWidth
        maxWidth="lg"
      >
        <DialogTitle>Customise Cluster Metrics</DialogTitle>
        <DialogContent>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: "12px",
            }}
          >
            {columnDescriptions.map((item) => (
              <FormControlLabel
                key={item.code}
                control={
                  <Checkbox
                    checked={selectedCodes.includes(item.code)}
                    onChange={() => handleCheckboxChange(item.code)}
                  />
                }
                label={
                  <div>
                    <strong>{item.name}</strong>
                    <div style={{ fontSize: "0.8rem", color: "#666" }}>
                      {item.description}
                    </div>
                  </div>
                }
              />
            ))}
          </div>
        </DialogContent>

        <DialogActions>
          <Button onClick={handleCancel}>Cancel</Button>
          <Button onClick={handleApply} variant="contained" color="primary">
            Apply
          </Button>
        </DialogActions>
      </Dialog>
    </AppLayout>
  );
};

export default ClusterMetricsPage;
