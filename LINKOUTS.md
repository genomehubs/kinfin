# Cluster ID Linkouts Feature

## Overview

The cluster ID linkouts feature allows you to define dynamic external links for clusters in table displays. This enables users to navigate from cluster IDs in the Kinfin UI to external resources (e.g., EnsemblDB, OrthoDB, internal annotation databases, etc.).

## Configuration

Linkouts are configured at the **clustering dataset level** in the [`src/api/clustering.json`](../src/api/clustering.json) file.

Each clustering dataset can define an array of `linkouts`, where each linkout specifies:

- `name`: Short display name for the resource chip (e.g., "Ensembl", "OrthoDB") — keep this **5-15 characters**
- `url_template`: URL template with field placeholders (e.g., `https://example.com/search?q={clusterId}`)
- `icon`: Icon file or path (see [Icon Configuration](#icon-configuration) below)
- `description`: Tooltip/hover text (optional)

### Schema Example

```json
{
  "id": "dataset-uuid",
  "name": "Dataset Name",
  "version": "v1.0",
  "date": "2025-05-10",
  "description": "Dataset description",
  "path": "dataset_path",
  "linkouts": [
    {
      "name": "Ensembl",
      "url_template": "https://ensembl.example.com/search?q={clusterId}",
      "icon": "ensembl.svg",
      "description": "Link to EnsemblDB cluster entry"
    },
    {
      "name": "OrthoDB",
      "url_template": "https://www.orthodb.org/?query={clusterId}",
      "icon": "orthodb.svg",
      "description": "View in OrthoDB"
    }
  ]
}
```

## Icon Configuration

### Adding Custom Icons

Custom icons are stored as SVG or PNG files in the **`src/ui/public/icons/linkouts/`** directory.

To add a new icon:

1. **Add SVG/PNG file** to [src/ui/public/icons/linkouts/](src/ui/public/icons/linkouts/)
   - Files should be standalone (all SVG contents in one file, no external references)
   - For SVGs: Use `currentColor` to support theming, or explicit colors
   - Recommended size: 24×24 px (will be scaled to 18×18 in chips)

2. **Update clustering.json** to reference the filename:

   ```json
   "icon": "myresource.svg"
   ```

3. **Example SVG icon** (18×24 px):
   ```svg
   <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
     <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none"/>
     <!-- Add your icon design here -->
   </svg>
   ```

### Icon Path Formats

The `icon` field supports flexible path formats:

- **Filename only**: `"ensembl.svg"` → loads from `/icons/linkouts/ensembl.svg`
- **Relative path**: `"resources/ensembl.svg"` → loads from `/icons/linkouts/resources/ensembl.svg`
- **Absolute path**: `"/custom/icons/ensembl.svg"` → loads from `/custom/icons/ensembl.svg`
- **Supported formats**: `.svg`, `.png`

### Built-in Icons

Pre-configured example icons (stored in [src/ui/public/icons/linkouts/](src/ui/public/icons/linkouts/)):

- `ensembl.svg` — For Ensembl Genome Browser
- `orthodb.svg` — For OrthoDB

### Icon Rendering Behavior

- Icons appear as **small images** in the chip display
- Failed icon loads are handled gracefully (chip displays without icon)
- Icons use `currentColor` for SVGs to blend with chip styling

## URL Templates

### Field Placeholders

URL templates support arbitrary field placeholders using the syntax `{fieldName}`. The resolver will substitute values from the cluster row data.

**Examples:**

- `https://example.com/cluster/{clusterId}` — Uses cluster ID
- `https://example.com/feature?id={clusterId}&attr={attribute}` — Uses multiple fields (when available in row data)
- `https://internal.example.com/anno/{annotationField}/{clusterId}` — Uses annotation field (future use case)

### Important Notes

- Placeholders are case-sensitive and must match field names in the row data
- Field values are automatically URL-encoded to handle special characters
- If a field is missing from row data, the linkout for that row will not be rendered
- Field names are in camelCase (e.g., `clusterId`, not `cluster_id`)

## Display Behavior

Linkouts are displayed in a dedicated "Links" column in the following tables:

- **ClusterSummary** table
- **ClusterMetrics** table

Linkouts are rendered as **clickable chips** with the configured name and icon. The layout automatically adapts to the number of links and available space.

### Rendering Modes

The component intelligently adapts the display based on the number of linkout resources:

| # Linkouts | Display                                                                  |
| ---------- | ------------------------------------------------------------------------ |
| 0          | Column hidden                                                            |
| 1          | Single full chip with name and icon                                      |
| 2-3        | All full chips displayed inline with names and icons                     |
| 4+         | First 3 chips as **icon-only** (with tooltips) + menu icon for remainder |

**For 4+ linkouts:**

- First 3 links display as compact **icon-only chips** (32×32 px)
- Hovering over icon shows tooltip with the full resource name
- Menu icon opens a dropdown showing all remaining resources with full names and icons
- Column width automatically adjusts (∼150-160 px) to fit without wrapping

### Column Width

The "Links" column width scales based on the display mode:

- **Single link**: ~80-200 px (depends on resource name length)
- **2-3 links**: ~200-300 px (scales with number and name lengths)
- **4+ links**: ∼152 px (3 icon-only chips + menu icon + gaps)

The width is automatically calculated and adjusted when the dataset loads.

### Column Visibility

- The "Links" column always appears if linkouts are configured for the dataset
- The column is **not** subject to the column selection (CS_code) parameter
- It appears at the end of the table, after all data columns

### Chip Interaction

- **Click chip**: Opens the link in a new browser tab
- **Hover tooltip**: Shows the `description` field
- **Overflow menu**: Click "+N" chip to see additional links in a dropdown menu

## Implementation Details

### Components

- **[`useClusterLinkouts`](../src/ui/src/app/hooks/useClusterLinkouts.js)** — Hook that resolves URL templates and determines render mode
- **[`ClusterLinkColumn`](../src/ui/src/components/Tables/ClusterLinkColumn.jsx)** — React component that renders the linkout buttons/menu

### Data Flow

1. **Init Endpoint** (`POST /kinfin/init`) returns linkouts from the clustering dataset config
2. **Redux State** stores linkouts in `config.data[sessionId].linkouts`
3. **Table Components** (ClusterSummary, ClusterMetrics) fetch linkouts from Redux and pass them to `ClusterLinkColumn`
4. **Hook** resolves templates and renders buttons/menu based on count

## Future Enhancements

The design supports future extensibility:

- **Annotation-based linkouts**: Add linkouts based on cell values (e.g., different links for different annotation types)
  - Example template: `https://example.com/anno/{annotationName}/{clusterId}`
  - Once annotation columns are added, templates automatically work

- **Attribute-specific linkouts**: Different linkouts for different attributes/outputs
  - No code changes needed for resolver; just add templates to separate attribute configs

- **Per-session linkout overrides**: Allow UI to customize linkouts per session
  - Would extend Redux state and RTK Query endpoints

## Troubleshooting

### Linkouts column not appearing

- **Check linkouts config**: Verify that the clustering dataset has a `linkouts` array in `clustering.json`
- **Check session init**: Verify that the `/kinfin/init` response includes the `linkouts` field in the data payload
- **Check Redux state**: In browser DevTools, check that `config.data[sessionId].linkouts` is populated

### Links not clickable or showing

- **Check URL template**: Verify that field names in the template match the actual row field names (case-sensitive, camelCase)
- **Check field values**: Verify that required fields exist in the table row data
- **Check icon names**: If icon isn't rendering, verify the icon name exists in MUI (@mui/icons-material)

### Special characters in URLs

Field values are automatically URL-encoded, so special characters (spaces, &, =, etc.) are handled safely.

## Testing

To test linkouts locally:

1. Update `clustering.json` with test linkout templates
2. Initialize a session via the UI (it will now return linkouts)
3. Navigate to ClusterSummary or ClusterMetrics table
4. Verify "Links" column appears
5. Click linkout buttons and verify URLs are correct and open external resources

## API Reference

### POST /kinfin/init

**Response (excerpt):**

```json
{
  "status": "success",
  "data": {
    "session_id": "abc-123",
    "linkouts": [
      {
        "name": "EnsemblDB",
        "url_template": "https://...",
        "icon": "DatabaseIcon",
        "description": "..."
      }
    ],
    "cluster_name": "Nematodes"
  }
}
```

**Linkouts Field:**

```typescript
linkouts: Array<{
  name: string; // Unique identifier/label
  url_template: string; // URL with field placeholders: {fieldName}
  icon?: string; // MUI icon component name
  description?: string; // Tooltip text
}>;
```
