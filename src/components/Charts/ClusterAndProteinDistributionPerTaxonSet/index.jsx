import styles from "./clusterAndProteinDistributionPerTaxonSet.module.scss";

import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import { useSelector } from "react-redux";

const ClusterAndProteinDistributionPerTaxonSet = () => {
  const svgRef = useRef();
  const wrapperRef = useRef();
  const legendRef = useRef();

  const data = useSelector(
    (state) => state?.analysis?.attributeSummary?.data?.data
  );

  useEffect(() => {
    if (!data || !wrapperRef.current) return;

    // Set dimensions based on parent container
    const containerWidth = wrapperRef.current.clientWidth;
    const margin = { top: 20, right: 30, bottom: 80, left: 60 }; // Increased bottom margin for legend
    const width = containerWidth - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    // Convert JSON into D3-friendly format
    const formattedData = Object.keys(data).map((key) => ({
      taxonSet: key,
      singleton: parseInt(data[key].singleton.cluster_count, 10),
      specific: parseInt(data[key].specific.cluster_count, 10),
      shared: parseInt(data[key].shared.cluster_count, 10),
    }));

    const stackKeys = ["singleton", "specific", "shared"];

    // Create scales
    const xScale = d3
      .scaleBand()
      .domain(formattedData.map((d) => d.taxonSet))
      .range([0, width])
      .padding(0.3);

    const yScale = d3
      .scaleLinear()
      .domain([
        0,
        d3.max(formattedData, (d) => d.singleton + d.specific + d.shared),
      ])
      .nice()
      .range([height, 0]);

    const colorScale = d3
      .scaleOrdinal()
      .domain(stackKeys)
      .range(["#ff6961", "#77dd77", "#84b6f4"]);

    // Create stack generator
    const stack = d3.stack().keys(stackKeys);
    const stackedData = stack(formattedData);

    // Select SVG and clear previous content
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Append group for chart
    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Tooltip setup
    const tooltip = d3
      .select(wrapperRef.current)
      .append("div")
      .style("position", "absolute")
      .style("background", "white")
      .style("color", "black")
      .style("padding", "6px")
      .style("border", "1px solid #ccc")
      .style("border-radius", "4px")
      .style("opacity", 0)
      .style("pointer-events", "none");

    // Draw bars
    g.selectAll("g")
      .data(stackedData)
      .enter()
      .append("g")
      .attr("fill", (d) => colorScale(d.key))
      .selectAll("rect")
      .data((d) => d)
      .enter()
      .append("rect")
      .attr("x", (d) => xScale(d.data.taxonSet))
      .attr("y", (d) => yScale(d[1]))
      .attr("height", (d) => yScale(d[0]) - yScale(d[1]))
      .attr("width", xScale.bandwidth())
      .on("mouseover", function (event, d) {
        tooltip
          .style("opacity", 1)
          .html(`Value: ${d[1] - d[0]}`)
          .style("left", `${event.pageX + 10}px`)
          .style("top", `${event.pageY - 10}px`);
        d3.select(this).style("opacity", 0.7);
      })
      .on("mousemove", (event) => {
        tooltip
          .style("left", `${event.pageX + 10}px`)
          .style("top", `${event.pageY - 10}px`);
      })
      .on("mouseout", function () {
        tooltip.style("opacity", 0);
        d3.select(this).style("opacity", 1);
      });
    // ✅ Apply zoom to the group, not the whole SVG
    const zoom = d3
      .zoom()
      .scaleExtent([1, 5]) // Min 1x, Max 5x zoom
      .translateExtent([
        [0, 0],
        [width, height],
      ])
      .on("zoom", (event) => {
        const newXScale = event.transform.rescaleX(xScale);

        // Update the x-axis with new scale
        g.select(".x-axis").call(d3.axisBottom(newXScale));

        // Update bars with new X positions
        g.selectAll("rect")
          .attr("x", (d) => newXScale(d.data.taxonSet))
          .attr("width", newXScale.bandwidth());
      });

    // ✅ Call zoom on the main group, not the SVG
    svg.call(zoom);

    // ✅ Prevent default scrolling behavior
    svg.on("wheel", (event) => event.preventDefault());
    // Add axes
    g.append("g")
      .attr("transform", `translate(0,${height})`)
      .attr("class", "x-axis") // Add class for selection
      .call(d3.axisBottom(xScale));

    g.append("g").call(d3.axisLeft(yScale));
    // Add x-axis label
    g.append("text")
      .attr("x", width / 2)
      .attr("y", height + margin.bottom - 30) // Position below the x-axis
      .attr("text-anchor", "middle")
      .attr("fill", "white")
      .style("font-size", "14px")
      .text("Taxon Set");

    // Add y-axis label
    g.append("text")
      .attr("transform", "rotate(-90)")
      .attr("x", -height / 2)
      .attr("y", -margin.left + 15) // Adjust left margin
      .attr("text-anchor", "middle")
      .attr("fill", "white")
      .style("font-size", "14px")
      .text("Cluster Count");

    // Update legend
    const legendContainer = d3.select(legendRef.current);
    legendContainer.selectAll("*").remove();

    legendContainer
      .selectAll("div")
      .data(stackKeys)
      .enter()
      .append("div")
      .attr("class", styles.legendItem) // Correct way to apply SCSS module class
      .each(function (key) {
        d3.select(this)
          .append("span")
          .attr("class", styles.legendColorBox) // Apply SCSS module class correctly
          .style("background", colorScale(key));

        d3.select(this).append("span").text(key);
      });
  }, [data]);

  return (
    <div ref={wrapperRef} className={styles.chartContainer}>
      <svg ref={svgRef} width="100%" height={380} />
      <div ref={legendRef} className={styles.legendContainer} />
    </div>
  );
};

export default ClusterAndProteinDistributionPerTaxonSet;
