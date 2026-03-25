import { useInitAnalysisMutation } from "#store/api";

export const useInitAnalysis = () => {
  const [initAnalysis, { isLoading, error }] = useInitAnalysisMutation();

  return { initAnalysis, isLoading, error };
};
