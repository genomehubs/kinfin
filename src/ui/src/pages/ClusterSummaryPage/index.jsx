import React, { useEffect, useState } from "react";
import styles from "./ClusterSummary.module.scss";
import AppLayout from "../../components/AppLayout";
import ClusterSummary from "../../components/Charts/ClusterSummary";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import { useDispatch, useSelector } from "react-redux";
import { getClusterSummary } from "../../app/store/analysis/slices/clusterSummarySlice";
import { dispatchSuccessToast } from "../../utils/toastNotifications";
import { setDownloadLoading } from "../../app/store/config/slices/uiStateSlice";
import { useSearchParams } from "react-router-dom";
import { getColumnDescriptions } from "../../app/store/config/actions";

import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Checkbox,
  Button,
} from "@mui/material";

const ClusterSummaryPage = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.uiState?.selectedAttributeTaxonset
  );
  const clusterSummaryDownloadLoading = useSelector(
    (state) => state?.config?.uiState?.downloadLoading?.clusterSummary
  );
  const columnDescriptions = useSelector(
    (state) => state?.config?.columnDescriptions?.data || []
  );

  const [customiseOpen, setCustomiseOpen] = useState(false);
  const [selectedCodes, setSelectedCodes] = useState([]);

  // Load selected codes from URL
  useEffect(() => {
    const paramsCodes = searchParams.getAll("CS_code");
    setSelectedCodes(paramsCodes);
  }, [searchParams]);
  useEffect(() => {
    dispatch(getColumnDescriptions({ file: "*.cluster_summary.txt" }));
  }, []);
  const handleDownload = () => {
    dispatch(setDownloadLoading({ type: "clusterSummary", loading: true }));
    const payload = {
      attribute: selectedAttributeTaxonset?.attribute,
      taxonSet: selectedAttributeTaxonset?.taxonset,
      asFile: true,
    };
    dispatchSuccessToast("Cluster Summary download has started");
    dispatch(getClusterSummary(payload));

    setTimeout(() => {
      dispatch(setDownloadLoading({ type: "clusterSummary", loading: false }));
    }, 30000);
  };

  const handleCustomisation = () => {
    setCustomiseOpen(true);
  };

  const handleCheckboxChange = (code) => {
    setSelectedCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const handleApply = () => {
    const newParams = new URLSearchParams(searchParams);
    newParams.delete("CS_code");
    selectedCodes.forEach((c) => newParams.append("CS_code", c));
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
            title="Cluster Summary"
            isDownloading={clusterSummaryDownloadLoading}
            onDownload={handleDownload}
            onCustomise={handleCustomisation}
          >
            <ClusterSummary />
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
        <DialogTitle>Customise Cluster Summary</DialogTitle>
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

export default ClusterSummaryPage;
