import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import styles from "./CountsByTaxon.module.scss"; // SCSS for styling

const CountsByTaxonChart = ({ data }) => {
  const chartRef = useRef();

  useEffect(() => {
    if (!data || Object.keys(data).length === 0) return;

    // Set dimensions
    const margin = { top: 50, right: 30, bottom: 80, left: 60 };
    const width = 800 - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    // Remove previous SVG to prevent duplicates
    d3.select(chartRef.current).selectAll("*").remove();

    // Create SVG canvas
    const svg = d3
      .select(chartRef.current)
      .append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Transform data into D3 stack format
    const taxa = Object.keys(Object.values(data)[0]); // Extract taxon names
    const stack = d3.stack().keys(taxa)(
      Object.entries(data).map(([key, values]) => ({
        orthogroup: key,
        ...values,
      }))
    );

    // Define scales
    const xScale = d3
      .scaleBand()
      .domain(Object.keys(data))
      .range([0, width])
      .padding(0.2);

    const yScale = d3
      .scaleLinear()
      .domain([0, d3.max(stack, (d) => d3.max(d, (d) => d[1]))])
      .nice()
      .range([height, 0]);

    const colorScale = d3.scaleOrdinal(d3.schemeCategory10).domain(taxa);

    // Create X axis
    svg
      .append("g")
      .attr("transform", `translate(0,${height})`)
      .call(d3.axisBottom(xScale))
      .selectAll("text")
      .attr("transform", "rotate(-45)")
      .style("text-anchor", "end")
      .style("fill", "white");

    // Create Y axis
    svg
      .append("g")
      .call(d3.axisLeft(yScale).tickFormat(d3.format("d")))
      .selectAll("text")
      .style("fill", "white");

    // Add grid lines
    svg
      .append("g")
      .attr("class", "grid")
      .call(d3.axisLeft(yScale).tickSize(-width).tickFormat(""))
      .style("stroke", "#555");

    // Tooltip
    const tooltip = d3
      .select(chartRef.current)
      .append("div")
      .attr("class", styles.tooltip)
      .style("opacity", 0);

    // Draw stacked bars
    svg
      .selectAll(".layer")
      .data(stack)
      .enter()
      .append("g")
      .attr("fill", (d) => colorScale(d.key))
      .selectAll("rect")
      .data((d) => d)
      .enter()
      .append("rect")
      .attr("x", (d) => xScale(d.data.orthogroup))
      .attr("y", (d) => yScale(d[1]))
      .attr("height", (d) => yScale(d[0]) - yScale(d[1]))
      .attr("width", xScale.bandwidth())
      .on("mouseover", (event, d) => {
        tooltip
          .style("opacity", 1)
          .html(`Count: ${d[1] - d[0]}`)
          .style("left", `${event.pageX + 10}px`)
          .style("top", `${event.pageY - 20}px`);
      })
      .on("mouseout", () => {
        tooltip.style("opacity", 0);
      });

    // Add legend
    const legend = svg
      .append("g")
      .attr("transform", `translate(${width - 150}, ${-30})`);

    taxa.forEach((taxon, i) => {
      legend
        .append("rect")
        .attr("x", 0)
        .attr("y", i * 20)
        .attr("width", 15)
        .attr("height", 15)
        .attr("fill", colorScale(taxon));

      legend
        .append("text")
        .attr("x", 20)
        .attr("y", i * 20 + 12)
        .style("fill", "white")
        .text(taxon);
    });
  }, [data]);

  return <div ref={chartRef} className={styles.chartContainer}></div>;
};

export default CountsByTaxonChart;
