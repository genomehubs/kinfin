import { FileUpload, Sidebar } from "../../components";
import AppLayout from "../../components/AppLayout";
import styles from "./DefineNodeLabels.module.scss";

const DefineNodeLabels = () => {
  return (
    <>
      <AppLayout>
        <div className={styles.page}>
          <FileUpload />
        </div>
      </AppLayout>
    </>
  );
};

export default DefineNodeLabels;
