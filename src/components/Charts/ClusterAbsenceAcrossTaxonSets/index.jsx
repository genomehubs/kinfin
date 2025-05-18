import styles from "./ClusterAbsenceAcrossTaxonSets.module.scss";

import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import { useSelector } from "react-redux";

const ClusterAbsenceAcrossTaxonSets = () => {
  const svgRef = useRef();
  const wrapperRef = useRef();
  const legendRef = useRef();

  const data = useSelector(
    (state) => state?.analysis?.attributeSummary?.data?.data
  );

  useEffect(() => {
    if (!data || !wrapperRef.current) return;

    const containerWidth = wrapperRef.current.clientWidth;
    const margin = { top: 20, right: 30, bottom: 80, left: 60 };
    const width = containerWidth - margin.left - margin.right;
    const height = 340 - margin.top - margin.bottom;

    const formattedData = Object.keys(data).map((key) => ({
      taxonSet: key,
      singleton: parseInt(data[key].absent.cluster_singleton_count, 10),
      specific: parseInt(data[key].absent.cluster_specific_count, 10),
      shared: parseInt(data[key].absent.cluster_shared_count, 10),
    }));

    const stackKeys = ["singleton", "specific", "shared"];

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
      .range(["#8FA6CB", "#A0D995", "#F4C2C2"]);

    const stack = d3.stack().keys(stackKeys);
    const stackedData = stack(formattedData);

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

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

    g.append("g")
      .attr("transform", `translate(0,${height})`)
      .call(d3.axisBottom(xScale))
      .selectAll("text") // Select all x-axis labels
      .style("text-anchor", "end") // Align text to the end for better readability
      .attr("transform", "rotate(-30)") // Rotate the labels by -30 degrees
      .attr("dy", "0.5em") // Adjust vertical position
      .attr("dx", "-0.5em"); // Adjust horizontal position

    g.append("g").call(d3.axisLeft(yScale));

    g.append("text")
      .attr("x", width / 2)
      .attr("y", height + margin.bottom - 20)
      .attr("text-anchor", "middle")
      .attr("fill", "white")
      .style("font-size", "14px")
      .text("Taxon Set");

    g.append("text")
      .attr("transform", "rotate(-90)")
      .attr("x", -height / 2)
      .attr("y", -margin.left + 10)
      .attr("text-anchor", "middle")
      .attr("fill", "white")
      .style("font-size", "14px")
      .text("Absent Cluster Count");

    const legendContainer = d3.select(legendRef.current);
    legendContainer.selectAll("*").remove();

    legendContainer
      .selectAll("div")
      .data(stackKeys)
      .enter()
      .append("div")
      .attr("class", styles.legendItem)
      .each(function (key) {
        d3.select(this)
          .append("span")
          .attr("class", styles.legendColorBox)
          .style("background", colorScale(key));

        d3.select(this).append("span").text(key);
      });
  }, [data]);

  return (
    <div ref={wrapperRef} className={styles.chartContainer}>
      <svg ref={svgRef} width="100%" height={350} />
      <div ref={legendRef} className={styles.legendContainer} />
    </div>
  );
};

export default ClusterAbsenceAcrossTaxonSets;
