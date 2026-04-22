import { Box, Chip, Menu, MenuItem } from "@mui/material";
import React, { useState, useRef } from "react";

import styles from "./ClusterLinkColumn.module.scss";
import { useClusterLinkouts } from "#app/hooks/useClusterLinkouts";

/**
 * Render an icon from either a file path or filename.
 * - If icon starts with '/', treat as absolute path
 * - If icon contains '.svg' or '.png', treat as relative path in /icons/linkouts/
 * - Otherwise, return null (will fall back to Chip's default icon)
 */
const renderCustomIcon = (icon) => {
  if (!icon) return null;

  let iconPath = icon;

  // If it's just a filename, prepend the icons directory
  if (!icon.startsWith("/") && !icon.startsWith("http")) {
    iconPath = `/icons/linkouts/${icon}`;
  }

  // Only support SVG and PNG files
  if (!iconPath.endsWith(".svg") && !iconPath.endsWith(".png")) {
    return null;
  }

  return (
    <img
      src={iconPath}
      alt="icon"
      style={{ width: 18, height: 18 }}
      onError={(e) => {
        // If icon fails to load, hide the img element
        e.target.style.display = "none";
      }}
    />
  );
};

/**
 * Custom cell renderer for cluster linkouts.
 * Display strategy:
 * - 1 link: Full chip with label
 * - 2-3 links: All full chips with labels
 * - 4+ links: First 3 as icon-only with tooltips, then menu for remaining
 */
const ClusterLinkColumn = ({ rowData, linkouts }) => {
  const [menuAnchorEl, setMenuAnchorEl] = useState(null);
  const menuOpen = Boolean(menuAnchorEl);
  const menuRef = useRef(null);

  const { links, renderMode } = useClusterLinkouts(linkouts, rowData);

  if (renderMode === "none" || links.length === 0) {
    return <></>;
  }

  const handleMenuClick = (event) => {
    event.stopPropagation();
    setMenuAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchorEl(null);
  };

  const handleChipClick = (url, event) => {
    event.preventDefault();
    event.stopPropagation();
    window.open(url, "_blank", "noopener,noreferrer");
  };

  /**
   * Render a full chip with label and icon/avatar
   */
  const renderFullChip = (link) => {
    const customIcon = renderCustomIcon(link.icon);
    return (
      <Chip
        key={link.name}
        label={link.name}
        size="small"
        onClick={(e) => handleChipClick(link.url, e)}
        title={link.description || link.name}
        avatar={
          customIcon ? (
            <Box sx={{ display: "flex", alignItems: "center" }}>
              {customIcon}
            </Box>
          ) : undefined
        }
        className={styles.linkChip}
        style={{ cursor: "pointer" }}
      />
    );
  };

  /**
   * Render an icon-only chip with tooltip - simple Box approach without MUI Chip overhead
   */
  const renderIconOnlyChip = (link) => {
    const customIcon = renderCustomIcon(link.icon);
    return (
      <Box
        key={link.name}
        onClick={(e) => handleChipClick(link.url, e)}
        title={link.description || link.name}
        className={styles.linkChipIconOnly}
      >
        {customIcon}
      </Box>
    );
  };

  // Determine layout based on number of links
  let displayLinks = links;
  let menuLinks = [];

  if (links.length >= 4) {
    // For 4+: show first 3 as icon-only, rest go to menu
    displayLinks = links.slice(0, 3);
    menuLinks = links.slice(3);
  }

  return (
    <Box className={styles.linkChipGroup}>
      {/* Display links with appropriate rendering */}
      {displayLinks.map((link) =>
        links.length >= 4 ? renderIconOnlyChip(link) : renderFullChip(link),
      )}

      {/* Menu button for 4+ links */}
      {menuLinks.length > 0 && (
        <>
          <Box
            ref={menuRef}
            onClick={handleMenuClick}
            title="More options"
            className={styles.linkChipIconOnly}
          >
            {renderCustomIcon("more.svg")}
          </Box>

          <Menu
            anchorEl={menuAnchorEl}
            open={menuOpen}
            onClose={handleMenuClose}
          >
            {links.map((link) => {
              const customIcon = renderCustomIcon(link.icon);
              return (
                <MenuItem
                  key={link.name}
                  onClick={(e) => {
                    handleChipClick(link.url, e);
                    handleMenuClose();
                  }}
                >
                  {customIcon && (
                    <Box
                      sx={{ mr: 1.5, display: "flex", alignItems: "center" }}
                    >
                      {customIcon}
                    </Box>
                  )}
                  <span>{link.name}</span>
                </MenuItem>
              );
            })}
          </Menu>
        </>
      )}
    </Box>
  );
};

export default ClusterLinkColumn;
