import React, { useState } from "react";
import styles from "./AttributeSummary.module.scss";
import AppLayout from "../../components/AppLayout";
import AttributeSummary from "../../components/Charts/AttributeSummary";
import AttributeSelector from "../../components/AttributeSelector";
import ChartCard from "../../components/ChartCard";
import { useDispatch, useSelector } from "react-redux";
import { getAttributeSummary } from "../../app/store/analysis/actions";
import { dispatchSuccessToast } from "../../utilis/tostNotifications";
import { setDownloadLoading } from "../../app/store/config/actions";
import BreadcrumbsNav from "../../components/BreadcrumbsNav";
import { Box } from "@mui/material";
import { useParams } from "react-router-dom";

const AttributeSummaryPage = () => {
  const dispatch = useDispatch();
  const selectedAttributeTaxonset = useSelector(
    (state) => state?.config?.selectedAttributeTaxonset
  );
  const downloadLoading = useSelector(
    (state) => state?.config?.downloadLoading
  );
  const { sessionId } = useParams();

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
  const breadcrumbItems = [
    { label: "Dashboard", href: `/${sessionId}/dashboard` },
    { label: "Attribute Summary", href: `/${sessionId}/attribute-summary` },
  ];

  return (
    <AppLayout>
      <Box mb={2}>
        <BreadcrumbsNav items={breadcrumbItems} />
      </Box>
      <div className={styles.pageHeader}>
        <AttributeSelector />
      </div>
      <div className={styles.page}>
        <div className={styles.chartsContainer}>
          <ChartCard
            title="Attribute Summary"
            isDownloading={downloadLoading?.downloadLoading?.attributeSummary}
            onDownload={handleDownload}
          >
            <AttributeSummary />
          </ChartCard>
        </div>
      </div>
    </AppLayout>
  );
};

export default AttributeSummaryPage;
