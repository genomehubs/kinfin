import React, { useEffect, useState } from "react";
import styles from "./AttributeSummary.module.scss";
import AppLayout from "../../components/AppLayout";
import AttributeSummary from "../../components/Charts/AttributeSummary";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import { useDispatch, useSelector } from "react-redux";
import { getAttributeSummary } from "../../app/store/analysis/actions";
import { dispatchSuccessToast } from "../../utilis/tostNotifications";
import { setDownloadLoading } from "../../app/store/config/actions";
import { useParams, useSearchParams } from "react-router-dom";

import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Checkbox,
  Button,
} from "@mui/material";

const CHECKLIST_DATA = [
  {
    code: "001",
    file: "cluster_counts_by_taxon.txt",
    name: "cluster_id",
    description: "Unique identifier for cluster",
  },
  {
    code: "002",
    file: "cluster_counts_by_taxon.txt",
    name: "taxon_id_X",
    description:
      "Count of proteins for each taxon_id within cluster (one column per taxon)",
  },
];
const AttributeSummaryPage = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.selectedAttributeTaxonset
  );
  const downloadLoading = useSelector(
    (state) => state?.config?.downloadLoading
  );
  const { sessionId } = useParams();

  const [customiseOpen, setCustomiseOpen] = useState(false);
  const [selectedCodes, setSelectedCodes] = useState([]);

  // On first render → check query params and set initial selection
  useEffect(() => {
    const paramsCodes = searchParams.getAll("AS_code"); // changed from "code"
    setSelectedCodes(paramsCodes);
  }, [searchParams]);

  const handleDownload = () => {
    dispatch(setDownloadLoading({ type: "attributeSummary", loading: true }));
    const payload = {
      attribute: selectedAttributeTaxonset?.attribute,
      taxonSet: selectedAttributeTaxonset?.taxonset,
      asFile: true,
    };
    dispatchSuccessToast("Attribute Summary download has started");
    dispatch(getAttributeSummary(payload));

    setTimeout(
      () =>
        dispatch(
          setDownloadLoading({ type: "attributeSummary", loading: false })
        ),
      30000
    );
  };

  const handleCustomisation = () => {
    setCustomiseOpen(true);
  };

  const handleCheckboxChange = (code) => {
    setSelectedCodes(
      (prev) =>
        prev.includes(code)
          ? prev.filter((c) => c !== code) // remove if exists
          : [...prev, code] // add if not exists
    );
  };

  const handleApply = () => {
    const newParams = new URLSearchParams(searchParams); // preserve other params
    // Remove existing AS_code params
    newParams.delete("AS_code");
    // Append new ones
    selectedCodes.forEach((c) => newParams.append("AS_code", c));
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
            title="Attribute Summary"
            isDownloading={downloadLoading?.downloadLoading?.attributeSummary}
            onDownload={handleDownload}
            onCustomise={handleCustomisation}
          >
            <AttributeSummary />
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
        <DialogTitle>Customise Attribute Summary</DialogTitle>
        <DialogContent>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: "12px",
            }}
          >
            {CHECKLIST_DATA.map((item) => (
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

export default AttributeSummaryPage;
