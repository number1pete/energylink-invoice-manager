# EnergyLink Website Analysis Report

> **Date**: February 8, 2026
> **URL**: https://app.energylink.com/
> **Account**: Thomas Claude Broome (cbbroome@gmail.com)
> **Platform Owner**: Enverus (formerly DrillingInfo)

---

## Overview

EnergyLink is an oil & gas royalty/revenue accounting portal operated by Enverus. It serves as a **non-operated (Non-Op) revenue statement viewer** where mineral rights owners can view their revenue checks, invoices, and per-well statement details from various operators.

### Authentication
- Login is handled via **Enverus Auth0 SSO** (login.auth.enverus.com)
- **SMS-based MFA** is enabled (sends 6-digit code to phone ending in 9741)
- After login, the user lands on the Dashboard

---

## Site Navigation & Page Hierarchy

```
Dashboard (Home)
  |
  +-- Dashboard Tab (quick recent view)
  +-- Invoices / Checks Tab (full list)
  |     |
  |     +-- Invoice Summary (per operator check)
  |           |
  |           +-- Statement Summary (per well/property)
  |
  +-- 1099 Tab (tax documents)
```

### Global Navigation Bar
- **Top bar**: EnergyLink logo (home link), Need Help?, Inbox (with unread count), File Manager, Enverus Apps link, User profile dropdown
- **Menu bar**: Search, Admin, Help & Info
- **Right side**: Contact Operator button, Operator Lists

---

## Page 1: Dashboard

**URL**: `https://app.energylink.com/Core/BSP/Dashboard`
**Title**: EnergyLink - Dashboard

### Tabs
| Tab | Description |
|-----|-------------|
| **Dashboard** | Quick-view of recent checks and invoices |
| **Invoices / Checks** | Full searchable/filterable grid of all invoices |
| **1099** | Tax documents |

### Dashboard Tab Content
Displays **"YOUR RECENT CHECKS AND INVOICES"** as a simple table:

| Column | Description |
|--------|-------------|
| Doc Type | e.g., "REVENUE" |
| Operator | Operator company name |
| Owner # | Owner identification number |
| Invoice/Check Date | Date of the invoice or check |
| View | Magnifying glass icon - links to Invoice Summary |
| PDF | PDF download icon |
| Excel | Excel download icon |

---

## Page 2: Invoices / Checks List

**URL**: `https://app.energylink.com/Core/BSP/Dashboard#invoices`
**Title**: EnergyLink - Dashboard (same page, different tab)

### Features
- **Search bar** with text input
- **Advanced Filters** toggle
- **Scroll Mode** dropdown (default: "Grid")
- **Show** dropdown for page size (default: 20)
- **Show Subtext** checkbox (checked by default)
- **Reset Filters** button
- **Bulk Archive / Bulk Unarchive** buttons (with row checkbox selection)
- **Pagination**: "1 to 20 of 105" with page navigation (6 pages total)

### Grid Columns (AG Grid)

| Column | Description | Sortable |
|--------|-------------|----------|
| Checkbox | Row selection for bulk operations | No |
| **Doc Type** | Document type (e.g., "REVENUE") | Yes |
| **Operator** | Operator company name (clickable link to Contact Operator Details) | Yes |
| **Owner #** | Owner identification number at the operator | Yes |
| **Invoice / Check** | Invoice or check number (primary line) + Invoice/Check Date (subtext) | Yes |
| **Op Acct Month** | Operator accounting month (primary line) + Received Date (subtext) | Yes |
| **Status** | Current status: "New", "Viewed" | Yes |
| **Total** | Total dollar amount (primary line) + Amt (subtext) + CSH (subtext) | Yes |
| **View** | Eye icon - navigates to Invoice Summary | No |
| **PDF** | PDF download icon | No |
| **Excel** | Excel download icon | No |
| **More** | Dropdown with additional actions | No |

### Data Note
- Shows **last 2 years of active invoices/checks**
- The Total amount is a clickable link that also navigates to the Invoice Summary

### Link Patterns
- **Operator name** links to: `/Core/BSP/ContactOperatorDetails?invoiceId={InvoiceId}`
- **Total amount / View icon** links to: `/Invoice/InvoiceSummary.aspx?InvoiceId={InvoiceId}&Context=Inbound`

---

## Page 3: Invoice Summary

**URL Pattern**: `https://app.energylink.com/Invoice/InvoiceSummary.aspx?InvoiceId={InvoiceId}&Context=Inbound`
**Title Format**: `EnergyLink - Non-Op REVENUE Check {CheckNumber} - {Date}`

### Header Section

| Field | Example Value |
|-------|---------------|
| Page Title | "Non-Op REVENUE Check 110355 - Jan 30, 2026" |
| Op Owner # | 88126 |
| Operator | TGNR PANOLA LLC |
| Owner | THOMAS CLAUDE BROOME |
| Internal Contact | thomas broome (User ID: 4085426, Default Contact) |
| Current Status | Viewed |

### Actions
| Action | Description |
|--------|-------------|
| **Download Invoice PDF** | Generates a PDF of the full invoice |
| **Download Invoice Excel** | Generates an Excel export of the full invoice |
| **Contact Operator** | Opens a message to the operator (links to `/Messages/CreateNewMessage.aspx?Context=Inbound&InvoiceId={InvoiceId}`) |
| **Archive** | Archives the invoice |
| **Invoice/Check Search** | Returns to the invoice search |
| **Messages** | Opens messaging |
| **View Address Info** | Expandable section for address details |

### Financial Summary Box

| Field | Example Value |
|-------|---------------|
| Check Number | 110355 |
| Revenue | 6,776.94 |
| Tax | (155.13) |
| Deductions | (895.53) |
| **Total** | **5,726.28** |

### Properties Table (Wells/Cost Centers)
Lists all properties (wells) included in this invoice. This example invoice had **14 properties**.

| Column | Description |
|--------|-------------|
| View icon | Eye icon linking to Statement Summary for that property |
| **Cost Center** | Numeric code identifying the property (e.g., 204381363) |
| **Description** | Well/property name (e.g., "ADAMS, T. C. NCT-1 C 1") |
| **State** | State abbreviation (e.g., "TX") |
| **County** | County name (e.g., "PANOLA") |
| **Owner Share Revenue** | Revenue attributable to owner |
| **Tax** | Tax amount (typically negative) |
| **Deductions** | Deduction amount (typically negative) |
| **Total** | Net total for this property |

### Properties Table Features
- **Show Subtext** checkbox
- Pagination indicator: "Properties 1 - 14"
- Columns are sortable (Cost Center, Description, State, County, Revenue, Tax, Deductions, Total)

### Example Properties (Invoice 593419797 - TGNR PANOLA LLC)

| Cost Center | Description | State | County | Revenue | Tax | Deductions | Total |
|------------|-------------|-------|--------|---------|-----|------------|-------|
| 204381363 | ADAMS, T. C. NCT-1 C 1 | TX | PANOLA | 651.88 | (31.98) | (127.38) | 492.52 |
| 204384661 | ADAMS, T. C. G/U NO. 1 O/A 2 | TX | PANOLA | 130.15 | (6.62) | (24.20) | 99.33 |
| 204384681 | CRENSHAW GAS UNIT NO. 1 2 | TX | PANOLA | 126.30 | (6.28) | (24.17) | 95.85 |
| 204385194 | ADAMS, T.C. NCT-1 44 F | TX | PANOLA | 630.65 | (30.94) | (123.23) | 476.48 |
| 204387201 | ADAMS, T. C. NCT-1 50 U | TX | PANOLA | 271.11 | (14.45) | (45.47) | 211.19 |
| 204419861 | CRENSHAW GAS UNIT #2 10 | TX | PANOLA | 69.32 | (3.58) | (12.40) | 53.34 |
| 204460801 | CRENSHAW GAS UNIT NO. 1 10 | TX | PANOLA | 45.67 | (2.53) | (6.72) | 36.42 |
| 204463603 | ADAMS, T.C. NCT-1 74 | TX | PANOLA | 159.74 | (7.64) | (33.04) | 119.06 |
| 204464772 | ADAMS, T. C. NCT-1 53 F | TX | PANOLA | 189.74 | (8.86) | (40.47) | 140.41 |
| 204466271 | CRENSHAW GAS UNIT NO. 1 16 | TX | PANOLA | 17.01 | (0.91) | (2.91) | 13.19 |
| 204479931 | ADAMS, T.C. GAS UNIT 1 O/A 5 | TX | PANOLA | 433.14 | (23.06) | (72.63) | 337.45 |
| 206054161 | ADAMS, T. C. NCT-1 61 | TX | PANOLA | 201.42 | (9.81) | (39.82) | 151.79 |
| 206252561 | ADAMS-BURNS 1HH | TX | PANOLA | 3,691.39 | (0.76) | (311.29) | 3,379.34 |
| 206339604 | ADAMS, T. C. NCT-1 C 1 | TX | PANOLA | 159.42 | (7.71) | (31.80) | 119.91 |

### Link Pattern
- **View icon / amounts** link to: `/Statement/StatementSummary.aspx?StatementId={StatementId}&Context=Inbound`

---

## Page 4: Statement Summary (Well Detail)

**URL Pattern**: `https://app.energylink.com/Statement/StatementSummary.aspx?StatementId={StatementId}&Context=Inbound`
**Title Format**: `EnergyLink - Non-Op REVENUE Check {CheckNumber} - Revenue Statement - {Date}`

### Header Section

| Field | Example Value |
|-------|---------------|
| Page Title | "Non-Op REVENUE Check 110355 - Revenue Statement - Jan 30, 2026" |
| Op Owner # | 88126 |
| Operator | TGNR PANOLA LLC |
| Owner | THOMAS CLAUDE BROOME |
| Code/Description | CC 204381363 - ADAMS, T. C. NCT-1 C 1 |
| API fields | Prt API #, Op API #, Env API # (empty in this example) |

### Actions
| Action | Description |
|--------|-------------|
| **Statement PDF** | Download individual statement as PDF |
| **Check** | Navigate back to Invoice Summary |
| **Messages** | Open messaging |

### Property Navigation
- Shows "Property X of Y" (e.g., "Property 1 of 14")
- **Previous Property** / **Next Property** arrows to navigate between wells within the same invoice
- Links directly to adjacent StatementIds

### Financial Summary Box (Same layout as Invoice Summary)

| Field | Example Value |
|-------|---------------|
| Check Number | 110355 |
| Revenue | 651.88 |
| Tax | (31.98) |
| Deductions | (127.38) |
| **Total** | **492.52** |

### Detail Line Items Table
The main data table showing all revenue and deduction line items for this specific well.

#### Columns

| Column | Description |
|--------|-------------|
| **Code** | Product/transaction code (e.g., "400.RI", "204.01") |
| **Type Desc** | Description of the code (e.g., "ROYALTY INTEREST", "COMPRESSION") |
| **Production Date** | Month/year of production (e.g., "Nov 25") |
| **BTU** | BTU factor (for gas products) |
| **Property Values - Volume** | Total property production volume |
| **Property Values - Price** | Unit price |
| **Property Values - Value** | Total property value |
| **Owner Share - Owner %** | Owner's percentage interest (e.g., 6.25000000%) |
| **Distribution %** | Distribution percentage |
| **Volume** | Owner's share of volume |
| **Value** | Owner's share of value (the actual dollar amount) |

#### Product Categories (Grouped with subtotals)

**PLANT PRODUCTS**
| Code | Type | Description |
|------|------|-------------|
| 400.RI | Revenue | ROYALTY INTEREST - the base revenue line with volume, price, value |
| 400.03 | Deduction | PROCESSING - plant processing fees |
| 400.FE | Tax | ENVIRONMENTAL TAX (GAS) |
| 400.PR | Tax | PRODUCTION TAX |

**RESIDUE GAS**
| Code | Type | Description |
|------|------|-------------|
| 204.RI | Revenue | ROYALTY INTEREST - base gas revenue with BTU, volume, price, value |
| 204.01 | Deduction | COMPRESSION |
| 204.05 | Deduction | TRANSPORTATION |
| 204.11 | Deduction | GATHERING |
| 204.FE | Tax | ENVIRONMENTAL TAX (GAS) |
| 204.PR | Tax | PRODUCTION TAX |

#### Subtotals
- **Total for PLANT PRODUCTS**: Volume subtotal + Value subtotal
- **Total for RESIDUE GAS**: Volume subtotal + Value subtotal
- **Total for Statement**: Combined Volume + Combined Value

### Example Statement Data (CC 204381363 - ADAMS, T. C. NCT-1 C 1)

#### Plant Products
| Code | Type | Prod Date | Volume | Price | Value | Owner % | Owner Volume | Owner Value |
|------|------|-----------|--------|-------|-------|---------|-------------|-------------|
| 400.RI | ROYALTY INTEREST | Nov 25 | 4,038.52 | 0.60 | 2,420.25 | 6.25% | 252.41 | 151.27 |
| 400.03 | PROCESSING | Nov 25 | | | (822.44) | 6.25% | | (51.40) |
| 400.FE | ENV TAX (GAS) | Nov 25 | | | 0.00 | 6.25% | | 0.00 |
| 400.PR | PRODUCTION TAX | Nov 25 | | | (119.84) | 6.25% | | (7.49) |
| | **Subtotal** | | | | | | **252.41** | **92.38** |

#### Residue Gas
| Code | Type | Prod Date | BTU | Volume | Price | Value | Owner % | Owner Volume | Owner Value |
|------|------|-----------|-----|--------|-------|-------|---------|-------------|-------------|
| 204.RI | ROYALTY INTEREST | Nov 25 | 1.02 | 2,486.86 | 3.22 | 8,009.80 | 6.25% | 155.43 | 500.61 |
| 204.01 | COMPRESSION | Nov 25 | | | | (711.85) | 6.25% | | (44.49) |
| 204.05 | TRANSPORTATION | Nov 25 | | | | (37.57) | 6.25% | | (2.35) |
| 204.11 | GATHERING | Nov 25 | | | | (466.19) | 6.25% | | (29.14) |
| 204.FE | ENV TAX (GAS) | Nov 25 | | | | (1.66) | 6.25% | | (0.10) |
| 204.PR | PRODUCTION TAX | Nov 25 | | | | (390.20) | 6.25% | | (24.39) |
| | **Subtotal** | | | | | | **155.43** | **400.14** |

**Statement Total**: Volume 407.84, Value **492.52**

---

## Known Operators & Owner Numbers

| Operator | Owner # | Typical Frequency |
|----------|---------|-------------------|
| TGNR PANOLA LLC | 88126 | Monthly |
| TGNR NLA LLC | 88126 | Monthly |
| SHERIDAN PRODUCTION COMPANY III, LLC | 70501 | Monthly |
| EXCO OPERATING COMPANY LP | 193061 | Monthly |
| BURK ROYALTY CO LTD | 26771 | Monthly |

---

## Key Data Relationships

```
Account (Thomas Claude Broome)
  |
  +-- Operator 1 (TGNR PANOLA LLC, Owner# 88126)
  |     +-- Invoice (Check# 110355, Jan 30 2026, Total $5,726.28)
  |     |     +-- Property 1 (CC 204381363 - ADAMS, T.C. NCT-1 C 1)
  |     |     |     +-- Plant Products lines (revenue, processing, taxes)
  |     |     |     +-- Residue Gas lines (revenue, compression, transport, gathering, taxes)
  |     |     +-- Property 2 (CC 204384661 - ADAMS, T.C. G/U NO. 1)
  |     |     |     +-- ... line items ...
  |     |     +-- ... 12 more properties ...
  |     +-- Invoice (Check# 108826, Dec 30 2025, Total $5,194.86)
  |     |     +-- ... properties and line items ...
  |     +-- ... more monthly invoices ...
  |
  +-- Operator 2 (TGNR NLA LLC, Owner# 88126)
  |     +-- ... invoices -> properties -> line items ...
  |
  +-- Operator 3 (SHERIDAN PRODUCTION COMPANY III, LLC, Owner# 70501)
  |     +-- ... invoices -> properties -> line items ...
  |
  +-- Operator 4 (EXCO OPERATING COMPANY LP, Owner# 193061)
  |     +-- ... invoices -> properties -> line items ...
  |
  +-- Operator 5 (BURK ROYALTY CO LTD, Owner# 26771)
  |     +-- ... invoices -> properties -> line items ...
```

---

## URL Patterns Summary

| Page | URL Pattern |
|------|-------------|
| Dashboard | `/Core/BSP/Dashboard` |
| Invoices Tab | `/Core/BSP/Dashboard#invoices` |
| 1099 Tab | `/Core/BSP/Dashboard#1099` |
| Invoice Summary | `/Invoice/InvoiceSummary.aspx?InvoiceId={id}&Context=Inbound` |
| Statement Summary | `/Statement/StatementSummary.aspx?StatementId={id}&Context=Inbound` |
| Contact Operator Details | `/Core/BSP/ContactOperatorDetails?invoiceId={id}` |
| Create Message | `/Messages/CreateNewMessage.aspx?Context=Inbound&InvoiceId={id}` |
| Messages Inbox | `/Messages/MessagesInbox.aspx` |
| Enverus Apps | `https://app.drillinginfo.com/gallery/` |

---

## Recent Invoice History (Sample Data)

| Operator | Check # | Date | Op Acct Month | Total |
|----------|---------|------|---------------|-------|
| TGNR PANOLA LLC | 110355 | 2026-01-30 | 2026-01-31 | $5,726.28 |
| TGNR NLA LLC | 200688 | 2026-01-30 | 2026-01-31 | $2,884.72 |
| SHERIDAN PRODUCTION CO III | 148588 | 2026-01-26 | 2026-01-31 | $639.30 |
| EXCO OPERATING CO LP | 4784830 | 2026-01-30 | 2026-01-31 | $2,882.27 |
| TGNR PANOLA LLC | 108826 | 2025-12-30 | 2025-12-31 | $5,194.86 |
| TGNR NLA LLC | 199626 | 2025-12-30 | 2025-12-31 | $2,306.18 |
| SHERIDAN PRODUCTION CO III | 147059 | 2025-12-29 | 2025-12-31 | $494.67 |
| EXCO OPERATING CO LP | 4781296 | 2025-12-31 | 2025-12-31 | $2,430.35 |
| BURK ROYALTY CO LTD | 0000198896 | 2026-01-12 | 2025-12-31 | $539.72 |
| TGNR PANOLA LLC | 108342 | 2025-11-26 | 2025-11-30 | $5,594.92 |
| TGNR NLA LLC | 199240 | 2025-11-26 | 2025-11-30 | $4,102.52 |
| SHERIDAN PRODUCTION CO III | 145525 | 2025-11-28 | 2025-11-30 | $989.64 |
| EXCO OPERATING CO LP | 4777902 | 2025-11-26 | 2025-11-30 | $4,235.56 |
| BURK ROYALTY CO LTD | 0000195274 | 2025-12-10 | 2025-11-30 | $1,032.54 |
| TGNR PANOLA LLC | 104505 | 2025-10-30 | 2025-10-31 | $6,062.16 |
| TGNR NLA LLC | 194811 | 2025-10-30 | 2025-10-31 | $3,853.69 |
| SHERIDAN PRODUCTION CO III | 144052 | 2025-10-28 | 2025-10-31 | $406.55 |
| EXCO OPERATING CO LP | 4774482 | 2025-10-31 | 2025-10-31 | $3,861.11 |
| BURK ROYALTY CO LTD | 0000191835 | 2025-11-10 | 2025-10-31 | $1,149.89 |
| TGNR PANOLA LLC | 103857 | 2025-09-29 | 2025-09-30 | $6,197.03 |

---

## Technical Notes

- **Frontend**: ASP.NET Web Forms (`.aspx` pages) mixed with a newer SPA section (`/Core/` routes using AG Grid, likely Vue or React)
- **Grid**: AG Grid for the Invoices/Checks list
- **Styling**: Older ASP.NET pages use table-based layout; newer dashboard uses modern CSS grid
- **Maps**: Google Maps JavaScript API is loaded (likely for asset mapping features)
- **Chat**: Zoom chat widget integrated
- **Export formats**: PDF and Excel available at both invoice and statement levels
