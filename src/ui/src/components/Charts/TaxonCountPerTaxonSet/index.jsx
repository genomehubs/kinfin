import styles from "./TaxonCountPerTaxonSet.module.scss";

import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import { useSelector } from "react-redux";

const TaxonCountPerTaxonSet = () => {
  const svgRef = useRef();
  const wrapperRef = useRef();
  const legendRef = useRef();

  const data = useSelector(
    (state) => state?.analysis?.attributeSummary?.data?.data
  );
  console.log("🚀 ~ TaxonCountPerTaxonSet ~ data:", data);

  useEffect(() => {
    if (!data || !wrapperRef.current) return;

    const containerWidth = wrapperRef.current.clientWidth;
    const margin = { top: 20, right: 30, bottom: 40, left: 50 };
    const width = containerWidth - margin.left - margin.right;
    const height = 300 - margin.top - margin.bottom;

    const formattedData = Object.keys(data).map((key) => ({
      taxonSet: key,
      count: parseInt(data[key].TAXON_count, 10),
    }));
    console.log("🚀 ~ formattedData ~ formattedData:", formattedData);

    const xScale = d3
      .scaleBand()
      .domain(formattedData.map((d) => d.taxonSet))
      .range([0, width])
      .padding(0.3);

    const yScale = d3
      .scaleLinear()
      .domain([0, d3.max(formattedData, (d) => d.count)])
      .nice()
      .range([height, 0]);

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    g.selectAll("rect")
      .data(formattedData)
      .enter()
      .append("rect")
      .attr("x", (d) => xScale(d.taxonSet))
      .attr("y", (d) => yScale(d.count))
      .attr("height", (d) => height - yScale(d.count))
      .attr("width", xScale.bandwidth())
      .attr("fill", "steelblue")
      .on("mouseover", function () {
        d3.select(this).attr("fill", "darkblue");
      })
      .on("mouseout", function () {
        d3.select(this).attr("fill", "steelblue");
      });

    g.append("g")
      .attr("transform", `translate(0,${height})`)
      .call(d3.axisBottom(xScale))
      .selectAll("text")
      .attr("transform", "rotate(-30)")
      .attr("text-anchor", "end");

    g.append("g").call(d3.axisLeft(yScale));
    // Add x-axis label
    g.append("text")
      .attr("x", width / 2)
      .attr("y", height + margin.bottom + 20) // Position below the x-axis
      .attr("text-anchor", "middle")
      .attr("fill", "white")
      .style("font-size", "14px")
      .text("Taxon Set");

    // Add y-axis label
    g.append("text")
      .attr("transform", "rotate(-90)")
      .attr("x", -height / 2)
      .attr("y", -margin.left + 10) // Adjust left margin
      .attr("text-anchor", "middle")
      .attr("fill", "white")
      .style("font-size", "14px")
      .text("Cluster Count");
  }, [data]);

  return (
    <div ref={wrapperRef} className={styles.chartContainer}>
      <svg ref={svgRef} width="100%" height={350}></svg>
      <div ref={legendRef} className={styles.legendContainer}></div>
    </div>
  );
};

export default TaxonCountPerTaxonSet;
