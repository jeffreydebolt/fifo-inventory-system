# Google Sheets API Integration - Design Document

## Overview

This document outlines the design for integrating Google Sheets API with the COGS Dashboard App to provide enhanced export capabilities and potential automatic synchronization. This integration will allow users to export COGS data with custom formatting and potentially maintain live-updated Google Sheets for client reporting.

## Requirements

Based on user feedback, the Google Sheets integration should:

1. Support exporting COGS data with custom formatting beyond basic CSV
2. Allow for calculated fields and pre-formatted columns in exports
3. Potentially support automatic synchronization for live data access
4. Maintain a professional, client-ready appearance in exported sheets

## Technical Approach

We will implement a two-phase approach:

### Phase 1: Enhanced Export Functionality
- Create a server-side function to generate properly formatted Google Sheets
- Support custom formatting, calculated fields, and data organization
- Provide users with shareable links to the generated sheets

### Phase 2: (Future) Automatic Synchronization
- Set up scheduled processes to update shared Google Sheets
- Implement change detection to minimize API usage
- Provide view-only links for clients

## Google Sheets API Implementation

### Authentication and Authorization

We will use OAuth 2.0 for authentication with the Google Sheets API:

1. **Service Account Approach**:
   - Create a Google Cloud project
   - Set up a service account with appropriate permissions
   - Generate and securely store service account credentials
   - This approach works best for server-side automation without user interaction

2. **User Consent Flow** (Alternative):
   - Implement OAuth 2.0 user consent flow
   - Store refresh tokens securely
   - This approach works best if users need to export to their own Google accounts

### Export Implementation

The export process will:

1. **Create a new Google Sheet** or use a template:
```javascript
async function createSheet(title) {
  const sheets = google.sheets({ version: 'v4', auth });
  const response = await sheets.spreadsheets.create({
    resource: {
      properties: {
        title,
      },
      sheets: [
        {
          properties: {
            title: 'COGS Summary',
            gridProperties: {
              rowCount: 1000,
              columnCount: 10
            }
          }
        },
        {
          properties: {
            title: 'COGS Details',
            gridProperties: {
              rowCount: 1000,
              columnCount: 15
            }
          }
        }
      ]
    }
  });
  return response.data.spreadsheetId;
}
```

2. **Apply formatting and structure**:
```javascript
async function formatSheet(spreadsheetId) {
  const sheets = google.sheets({ version: 'v4', auth });
  
  // Apply header formatting
  await sheets.spreadsheets.batchUpdate({
    spreadsheetId,
    resource: {
      requests: [
        {
          repeatCell: {
            range: {
              sheetId: 0,
              startRowIndex: 0,
              endRowIndex: 1,
            },
            cell: {
              userEnteredFormat: {
                backgroundColor: { red: 0.6, green: 0.6, blue: 0.9 },
                textFormat: { bold: true, foregroundColor: { red: 1, green: 1, blue: 1 } },
                horizontalAlignment: 'CENTER',
              }
            },
            fields: 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
          }
        },
        // Additional formatting requests...
      ]
    }
  });
}
```

3. **Populate with data**:
```javascript
async function populateSheet(spreadsheetId, data) {
  const sheets = google.sheets({ version: 'v4', auth });
  
  // Write headers
  await sheets.spreadsheets.values.update({
    spreadsheetId,
    range: 'COGS Summary!A1:F1',
    valueInputOption: 'USER_ENTERED',
    resource: {
      values: [['Month', 'SKU', 'Total Units Sold', 'COGS (Unit Cost)', 'COGS (Freight Cost)', 'Total COGS']]
    }
  });
  
  // Write data
  await sheets.spreadsheets.values.update({
    spreadsheetId,
    range: 'COGS Summary!A2',
    valueInputOption: 'USER_ENTERED',
    resource: {
      values: data.map(row => [
        row.month,
        row.sku,
        row.total_quantity_sold,
        row.total_cogs_unit_only,
        row.total_cogs_freight_only,
        row.total_cogs_blended
      ])
    }
  });
}
```

4. **Add calculated fields and formulas**:
```javascript
async function addCalculations(spreadsheetId) {
  const sheets = google.sheets({ version: 'v4', auth });
  
  // Add summary formulas
  await sheets.spreadsheets.values.update({
    spreadsheetId,
    range: 'COGS Summary!A1000:F1000',
    valueInputOption: 'USER_ENTERED',
    resource: {
      values: [
        ['TOTAL', '', '=SUM(C2:C999)', '=SUM(D2:D999)', '=SUM(E2:E999)', '=SUM(F2:F999)']
      ]
    }
  });
  
  // Add conditional formatting
  await sheets.spreadsheets.batchUpdate({
    spreadsheetId,
    resource: {
      requests: [
        {
          addConditionalFormatRule: {
            rule: {
              ranges: [{ sheetId: 0, startRowIndex: 1, endRowIndex: 999, startColumnIndex: 5, endColumnIndex: 6 }],
              gradientRule: {
                minpoint: { color: { red: 1, green: 1, blue: 1 }, type: 'MIN' },
                maxpoint: { color: { red: 0.8, green: 0.3, blue: 0.3 }, type: 'MAX' }
              }
            },
            index: 0
          }
        }
      ]
    }
  });
}
```

5. **Create charts and visualizations**:
```javascript
async function addCharts(spreadsheetId) {
  const sheets = google.sheets({ version: 'v4', auth });
  
  await sheets.spreadsheets.batchUpdate({
    spreadsheetId,
    resource: {
      requests: [
        {
          addChart: {
            chart: {
              spec: {
                title: 'Monthly COGS Trend',
                basicChart: {
                  chartType: 'LINE',
                  legendPosition: 'BOTTOM_LEGEND',
                  axis: [
                    { position: 'BOTTOM_AXIS', title: 'Month' },
                    { position: 'LEFT_AXIS', title: 'COGS ($)' }
                  ],
                  domains: [
                    { domain: { sourceRange: { sources: [{ sheetId: 0, startRowIndex: 1, endRowIndex: 13, startColumnIndex: 0, endColumnIndex: 1 }] } } }
                  ],
                  series: [
                    { series: { sourceRange: { sources: [{ sheetId: 0, startRowIndex: 1, endRowIndex: 13, startColumnIndex: 5, endColumnIndex: 6 }] } } }
                  ]
                }
              },
              position: {
                overlayPosition: {
                  anchorCell: { sheetId: 0, rowIndex: 3, columnIndex: 8 },
                  widthPixels: 600,
                  heightPixels: 400
                }
              }
            }
          }
        }
      ]
    }
  });
}
```

6. **Set permissions and generate shareable link**:
```javascript
async function shareSheet(spreadsheetId) {
  const drive = google.drive({ version: 'v3', auth });
  
  await drive.permissions.create({
    fileId: spreadsheetId,
    requestBody: {
      role: 'reader',
      type: 'anyone',
    }
  });
  
  const result = await drive.files.get({
    fileId: spreadsheetId,
    fields: 'webViewLink'
  });
  
  return result.data.webViewLink;
}
```

### Automatic Synchronization (Phase 2)

For automatic synchronization, we will:

1. **Create template sheets** for each client or reporting need
2. **Set up a scheduled process** to update these sheets:
   - Cloud Function or server-side cron job
   - Triggered daily or on data changes
   - Updates only changed data to minimize API usage

3. **Implement change detection**:
   - Track last update timestamp
   - Compare with latest data changes
   - Only update sheets when data has changed

4. **Provide view-only links** to clients:
   - Generate once and store in the database
   - Associate with client accounts if applicable
   - Include in client communications

## UI Integration

### Export Button and Options

The UI will include:

1. **Export Dropdown** with options:
   - Export as CSV (existing functionality)
   - Export to Google Sheets (new)
   - Schedule Regular Reports (future)

2. **Export Configuration Modal**:
   - Sheet title and description
   - Data range selection
   - Format options (currency, date format)
   - Chart inclusion options

3. **Export Progress Indicator**:
   - Shows status during export process
   - Provides shareable link when complete

### Mockup

```
+-----------------------------------------------+
|  FIFO Inventory                      [Settings]|
+-----------------------------------------------+
| [Dashboard] [Inventory] [Transactions] [Reports]
+-----------------------------------------------+
|                                               |
| Monthly COGS Breakdown                        |
|                                               |
| Filters: [Date Range ▼] [SKU ▼] [Clear All]   |
|                                               |
| +-------------------------------------------+ |
| | Month | SKU | Units | Unit Cost | Freight | |
| |-------|-----|-------|-----------|---------|
| | May.. | FB..| 654   | $10,234   | $1,308  | |
| | Apr.. | FB..| 598   | $9,568    | $1,196  | |
| | Mar.. | FB..| 702   | $11,232   | $1,404  | |
| +-------------------------------------------+ |
|                                               |
| [Export ▼]                                    |
|  ┌─────────────────┐                          |
|  │ Export as CSV   │                          |
|  │ Export to Sheets│                          |
|  │ Schedule Reports│                          |
|  └─────────────────┘                          |
+-----------------------------------------------+

// When "Export to Sheets" is selected:

+-----------------------------------------------+
| Export to Google Sheets                    [X] |
+-----------------------------------------------+
|                                               |
| Sheet Title:                                  |
| [COGS Report - May 2025                     ] |
|                                               |
| Data Range:                                   |
| [Last 12 Months ▼]                            |
|                                               |
| Include:                                      |
| [✓] Summary Sheet                             |
| [✓] Detailed Breakdown                        |
| [✓] Charts and Visualizations                 |
|                                               |
| Format:                                       |
| [✓] Currency Formatting                       |
| [✓] Color Coding by Value                     |
| [✓] Totals and Subtotals                      |
|                                               |
| [Cancel]                [Create Sheet]        |
+-----------------------------------------------+
```

## Implementation Plan

### Phase 1: Basic Google Sheets Export

1. Set up Google Cloud project and API credentials
2. Implement server-side function for sheet creation and formatting
3. Create UI components for export options
4. Implement export process with progress indication
5. Add shareable link generation and display

### Phase 2: Enhanced Formatting and Templates

1. Create template system for different report types
2. Implement advanced formatting options
3. Add charts and visualization generation
4. Support for calculated fields and formulas

### Phase 3: Automatic Synchronization (Future)

1. Implement change detection system
2. Create scheduled update process
3. Add client management for shared reports
4. Implement notification system for report updates

## Security Considerations

1. **API Credentials**: Store securely using environment variables or secret management
2. **Access Control**: Implement proper permissions for shared sheets
3. **Data Privacy**: Ensure sensitive data is not included in shared reports
4. **Rate Limiting**: Implement safeguards to prevent API quota exhaustion

## Next Steps

1. Set up Google Cloud project and enable Sheets API
2. Create service account and generate credentials
3. Implement basic sheet creation and formatting functions
4. Develop UI components for export configuration
5. Test with sample COGS data
6. Document usage for end users
