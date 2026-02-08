/**
 * DataTables initialization and CSV export for Dashboard tables.
 */

let rollupDT = null;
let rawDT = null;

function fmt(val, decimals = 2) {
    if (val === null || val === undefined) return "";
    return Number(val).toFixed(decimals);
}

function fmtDollar(val) {
    if (val === null || val === undefined) return "";
    return "$" + Number(val).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtNum(val) {
    if (val === null || val === undefined) return "";
    return Number(val).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function renderRollupTable(data) {
    if (rollupDT) {
        rollupDT.destroy();
        document.getElementById("rollup-table").innerHTML = "";
    }

    rollupDT = new DataTable("#rollup-table", {
        data: data,
        columns: [
            { data: "production_date", title: "Month" },
            { data: "revenue", title: "Revenue", render: (d) => fmtDollar(d) },
            { data: "volume", title: "Volume (MCF)", render: (d) => fmtNum(d) },
            { data: "revenue_per_mcf", title: "Rev $/MCF", render: (d) => fmtDollar(d) },
            { data: "avg_price", title: "Avg Price", render: (d) => fmtDollar(d) },
            { data: "gathering_per_mcf", title: "Gather $/MCF", render: (d) => fmtDollar(d) },
            { data: "processing_per_mcf", title: "Process $/MCF", render: (d) => fmtDollar(d) },
            { data: "compression_per_mcf", title: "Compr $/MCF", render: (d) => fmtDollar(d) },
            { data: "transportation_per_mcf", title: "Trans $/MCF", render: (d) => fmtDollar(d) },
            { data: "taxes_per_mcf", title: "Tax $/MCF", render: (d) => fmtDollar(d) },
            { data: "total_expenses_per_mcf", title: "Tot Exp $/MCF", render: (d) => fmtDollar(d) },
            { data: "net_per_mcf", title: "Net $/MCF", render: (d) => fmtDollar(d) },
        ],
        order: [],
        paging: false,
        searching: false,
        info: false,
        layout: {
            topStart: {
                buttons: [
                    { extend: "csv", text: "Export CSV", className: "btn btn-sm btn-outline-secondary" }
                ]
            }
        },
    });
}

function renderRawTable(data) {
    if (rawDT) {
        rawDT.destroy();
        document.getElementById("raw-table").innerHTML = "";
    }

    rawDT = new DataTable("#raw-table", {
        data: data,
        columns: [
            { data: "production_date", title: "Month" },
            { data: "operator", title: "Operator" },
            { data: "property", title: "Property" },
            { data: "category", title: "Category" },
            { data: "code", title: "Code" },
            { data: "type_description", title: "Type" },
            { data: "volume", title: "Volume", render: (d) => fmtNum(d) },
            { data: "price", title: "Price", render: (d) => fmtDollar(d) },
            { data: "value", title: "Value", render: (d) => fmtDollar(d) },
            { data: "owner_pct", title: "Owner %", render: (d) => fmt(d, 4) },
            { data: "owner_volume", title: "Owner Vol", render: (d) => fmtNum(d) },
            { data: "owner_value", title: "Owner Value", render: (d) => fmtDollar(d) },
        ],
        order: [],
        pageLength: 25,
        layout: {
            topStart: {
                buttons: [
                    { extend: "csv", text: "Export CSV", className: "btn btn-sm btn-outline-secondary" }
                ]
            }
        },
    });
}
