import React, { useEffect } from "react";
import { getColumnDescriptions } from "../../app/store/config/actions";
import { useDispatch, useSelector } from "react-redux";
import ChipComboBox from "../../components/UIElements/ChipComboBox";
import styles from "./CustomTable.module.scss";
import AppLayout from "../../components/AppLayout";
import AttributeSelector from "../../components/AttributeSelector";

const CustomTable = () => {
  const dispatch = useDispatch();
  const columnDescriptions = useSelector(
    (state) => state?.config?.columnDescriptions?.data
  );

  useEffect(() => {
    dispatch(getColumnDescriptions());
  }, []);

  return (
    <>
      {" "}
      <AppLayout>
        <div className={styles.pageHeader}>
          <AttributeSelector />
        </div>
        <div className={styles.page}>
          Select your own columns
          {columnDescriptions && (
            <ChipComboBox options={columnDescriptions} />
          )}{" "}
        </div>
      </AppLayout>
    </>
  );
};

export default CustomTable;
