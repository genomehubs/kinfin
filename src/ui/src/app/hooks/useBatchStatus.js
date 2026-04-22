import { useGetBatchStatusMutation } from "#store/api";

export const useBatchStatus = () => {
  return useGetBatchStatusMutation();
};
