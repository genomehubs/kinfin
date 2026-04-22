import { useMemo } from "react";

/**
 * Resolves URL templates with field placeholders.
 * Supports arbitrary {fieldName} patterns and substitutes from rowData.
 *
 * @param {string} template - URL template with {fieldName} placeholders
 * @param {object} rowData - Object containing field values to substitute
 * @returns {string|null} - Resolved URL or null if substitution fails
 */
const resolveUrlTemplate = (template, rowData) => {
  if (!template || !rowData) return null;

  try {
    // Match all {fieldName} patterns
    const placeholderRegex = /\{([^}]+)\}/g;
    let resolvedUrl = template;
    let hasUnresolvedPlaceholder = false;

    resolvedUrl = template.replace(placeholderRegex, (match, fieldName) => {
      const value = rowData[fieldName];
      if (value === undefined || value === null) {
        hasUnresolvedPlaceholder = true;
        return match; // Keep original placeholder if field not found
      }
      // URL encode the value to handle special characters
      return encodeURIComponent(String(value));
    });

    // Don't return URL if there were unresolved placeholders
    if (hasUnresolvedPlaceholder) {
      return null;
    }

    return resolvedUrl;
  } catch (error) {
    console.warn("Error resolving URL template:", template, error);
    return null;
  }
};

/**
 * Hook to resolve linkout URLs and determine render mode.
 *
 * @param {array} linkouts - Array of linkout config objects: { name, urlTemplate (or url_template), icon?, description? }
 * @param {object} rowData - Full row data object containing field values
 * @returns {object} - Resolved linkout data with render mode: { links: { name, url, icon, description }[], renderMode: 'single'|'multi'|'menu'|'none' }
 */
export const useClusterLinkouts = (linkouts, rowData) => {
  return useMemo(() => {
    if (!linkouts || linkouts.length === 0 || !rowData) {
      return { links: [], renderMode: "none" };
    }

    // Resolve all URLs from templates
    const resolvedLinks = linkouts
      .map((linkout) => {
        const template = linkout.urlTemplate || linkout.url_template;
        const url = resolveUrlTemplate(template, rowData);
        return {
          name: linkout.name,
          url,
          icon: linkout.icon || "LinkIcon",
          description: linkout.description,
        };
      })
      .filter((link) => link.url !== null); // Filter out any that failed to resolve

    if (resolvedLinks.length === 0) {
      return { links: [], renderMode: "none" };
    }

    let renderMode = "none";
    if (resolvedLinks.length === 1) {
      renderMode = "single";
    } else if (resolvedLinks.length <= 3) {
      renderMode = "multi";
    } else {
      renderMode = "menu";
    }

    return { links: resolvedLinks, renderMode };
  }, [linkouts, rowData]);
};
