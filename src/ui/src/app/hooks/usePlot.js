import { useGetPlotQuery } from "#store/api";

const usePlot = ({ attribute, plotType }, options = {}) => {
  return useGetPlotQuery({ attribute, plotType }, options);
};

export default usePlot;
