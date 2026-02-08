/**
 * Plotly chart rendering for the Dashboard tab.
 * Charts auto-fill their resizable containers via ResizeObserver.
 */

// Available line chart series
const LINE_SERIES = [
    { key: "revenue_per_mcf", label: "Revenue $/MCF", color: "#2ecc71", defaultOn: true, yaxis: "y" },
    { key: "avg_price", label: "Avg Price", color: "#3498db", defaultOn: true, yaxis: "y2" },
    { key: "total_expenses_per_mcf", label: "Total Expenses $/MCF", color: "#e74c3c", defaultOn: true, yaxis: "y" },
    { key: "net_per_mcf", label: "Net $/MCF", color: "#f39c12", defaultOn: false, yaxis: "y" },
    { key: "gathering_per_mcf", label: "Gathering $/MCF", color: "#9b59b6", defaultOn: false, yaxis: "y" },
    { key: "processing_per_mcf", label: "Processing $/MCF", color: "#1abc9c", defaultOn: false, yaxis: "y" },
    { key: "compression_per_mcf", label: "Compression $/MCF", color: "#e67e22", defaultOn: false, yaxis: "y" },
    { key: "transportation_per_mcf", label: "Transportation $/MCF", color: "#34495e", defaultOn: false, yaxis: "y" },
    { key: "taxes_per_mcf", label: "Taxes $/MCF", color: "#95a5a6", defaultOn: false, yaxis: "y" },
    { key: "marketing_per_mcf", label: "Marketing $/MCF", color: "#d35400", defaultOn: false, yaxis: "y" },
    { key: "volume", label: "Volume (MCF)", color: "#7f8c8d", defaultOn: false, yaxis: "y2" },
];

let lineSeriesState = {};

function buildLineToggles() {
    const container = document.getElementById("line-chart-toggles");
    container.innerHTML = "";
    LINE_SERIES.forEach(s => {
        if (!(s.key in lineSeriesState)) lineSeriesState[s.key] = s.defaultOn;
        const id = "toggle-" + s.key;
        const div = document.createElement("div");
        div.className = "form-check form-check-inline";
        div.innerHTML = `
            <input class="form-check-input" type="checkbox" id="${id}"
                   ${lineSeriesState[s.key] ? "checked" : ""}>
            <label class="form-check-label" for="${id}" style="color:${s.color}">${s.label}</label>
        `;
        div.querySelector("input").addEventListener("change", (e) => {
            lineSeriesState[s.key] = e.target.checked;
            renderLineChart(window._lastMonthly);
        });
        container.appendChild(div);
    });
}

function renderLineChart(data) {
    window._lastMonthly = data;
    buildLineToggles();

    const x = data.map(d => d.production_date);
    const traces = [];

    LINE_SERIES.forEach(s => {
        if (!lineSeriesState[s.key]) return;
        traces.push({
            x: x,
            y: data.map(d => d[s.key]),
            name: s.label,
            type: "scatter",
            mode: "lines+markers",
            line: { color: s.color, width: 2 },
            marker: { size: 4 },
            yaxis: s.yaxis,
            connectgaps: true,
        });
    });

    const layout = {
        margin: { t: 20, r: 60, b: 40, l: 60 },
        autosize: true,
        legend: { orientation: "h", y: -0.2 },
        xaxis: { title: "" },
        yaxis: { title: "$/MCF", side: "left" },
        yaxis2: { title: "Price / Volume", side: "right", overlaying: "y" },
    };

    Plotly.react("line-chart", traces, layout, { responsive: true });
}


// Combo chart - bar + line
const COMBO_OPTIONS = [
    { key: "revenue", label: "Revenue ($)" },
    { key: "volume", label: "Volume (MCF)" },
    { key: "total_expenses", label: "Total Expenses ($)" },
    { key: "avg_price", label: "Avg Price ($/MCF)" },
    { key: "revenue_per_mcf", label: "Revenue $/MCF" },
    { key: "net_per_mcf", label: "Net $/MCF" },
    { key: "gathering_expense", label: "Gathering ($)" },
    { key: "processing_expense", label: "Processing ($)" },
    { key: "compression_expense", label: "Compression ($)" },
    { key: "transportation_expense", label: "Transportation ($)" },
    { key: "taxes_expense", label: "Taxes ($)" },
];

let comboInited = false;

function initComboSelects() {
    if (comboInited) return;
    comboInited = true;

    const barSel = document.getElementById("combo-bar-select");
    const lineSel = document.getElementById("combo-line-select");

    COMBO_OPTIONS.forEach(o => {
        barSel.add(new Option(o.label, o.key));
        lineSel.add(new Option(o.label, o.key));
    });

    // Defaults
    barSel.value = "revenue";
    lineSel.value = "avg_price";

    barSel.addEventListener("change", () => renderComboChart(window._lastMonthly));
    lineSel.addEventListener("change", () => renderComboChart(window._lastMonthly));
}

function renderComboChart(data) {
    initComboSelects();
    window._lastMonthly = data;

    const barKey = document.getElementById("combo-bar-select").value;
    const lineKey = document.getElementById("combo-line-select").value;
    const barLabel = COMBO_OPTIONS.find(o => o.key === barKey)?.label || barKey;
    const lineLabel = COMBO_OPTIONS.find(o => o.key === lineKey)?.label || lineKey;

    const x = data.map(d => d.production_date);

    const traces = [
        {
            x: x,
            y: data.map(d => d[barKey]),
            name: barLabel,
            type: "bar",
            marker: { color: "#3498db" },
            yaxis: "y",
        },
        {
            x: x,
            y: data.map(d => d[lineKey]),
            name: lineLabel,
            type: "scatter",
            mode: "lines+markers",
            line: { color: "#e74c3c", width: 2 },
            marker: { size: 5 },
            yaxis: "y2",
        },
    ];

    const layout = {
        margin: { t: 20, r: 60, b: 40, l: 60 },
        autosize: true,
        legend: { orientation: "h", y: -0.2 },
        xaxis: { title: "" },
        yaxis: { title: barLabel, side: "left" },
        yaxis2: { title: lineLabel, side: "right", overlaying: "y" },
        barmode: "group",
    };

    Plotly.react("combo-chart", traces, layout, { responsive: true });
}


// ResizeObserver: relay container resizes to Plotly
const _chartResizeObserver = new ResizeObserver(entries => {
    for (const entry of entries) {
        const plotDiv = entry.target.querySelector("[class*='plot-container']")?.parentElement;
        if (plotDiv) {
            Plotly.Plots.resize(plotDiv);
        }
    }
});

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".chart-resize-container").forEach(el => {
        _chartResizeObserver.observe(el);
    });
});
