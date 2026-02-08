/**
 * SPA tab routing, filter initialization, and data loading.
 */

let filterChoices = {};

// Month sort helper: converts "Mon YY" to sortable "YYYY-MM"
const MONTH_MAP = {
    Jan: "01", Feb: "02", Mar: "03", Apr: "04", May: "05", Jun: "06",
    Jul: "07", Aug: "08", Sep: "09", Oct: "10", Nov: "11", Dec: "12"
};

function monthSortKey(dateStr) {
    if (!dateStr) return "";
    const parts = dateStr.split(" ");
    if (parts.length !== 2) return dateStr;
    const mon = MONTH_MAP[parts[0]] || "00";
    const yr = parts[1].length === 2 ? "20" + parts[1] : parts[1];
    return yr + "-" + mon;
}

function sortByMonth(a, b) {
    return monthSortKey(a).localeCompare(monthSortKey(b));
}

// Initialize filter dropdowns with Choices.js
function initFilters(options) {
    filterChoices.operator = new Choices("#filter-operator", {
        removeItemButton: true, placeholderValue: "All operators", searchPlaceholderValue: "Search..."
    });
    filterChoices.operator.setChoices(
        options.operators.map(o => ({ value: o, label: o })), "value", "label", true
    );

    filterChoices.property = new Choices("#filter-property", {
        removeItemButton: true, placeholderValue: "All properties", searchPlaceholderValue: "Search..."
    });
    filterChoices.property.setChoices(
        options.properties.map(p => ({ value: p, label: p })), "value", "label", true
    );

    filterChoices.category = new Choices("#filter-category", {
        removeItemButton: true, placeholderValue: "All categories", searchPlaceholderValue: "Search..."
    });
    filterChoices.category.setChoices(
        options.categories.map(c => ({ value: c, label: c })), "value", "label", true
    );

    // Date range dropdowns - sort chronologically
    const sortedDates = [...options.all_dates].sort(sortByMonth);
    const startSel = document.getElementById("filter-date-start");
    const endSel = document.getElementById("filter-date-end");
    sortedDates.forEach(d => {
        startSel.add(new Option(d, d));
        endSel.add(new Option(d, d));
    });
}

// Collect current filter values
function getFilterParams() {
    const params = new URLSearchParams();

    const ops = filterChoices.operator.getValue(true);
    ops.forEach(o => params.append("operators", o));

    const props = filterChoices.property.getValue(true);
    props.forEach(p => params.append("properties", p));

    const cats = filterChoices.category.getValue(true);
    cats.forEach(c => params.append("categories", c));

    const ds = document.getElementById("filter-date-start").value;
    if (ds) params.set("date_start", ds);

    const de = document.getElementById("filter-date-end").value;
    if (de) params.set("date_end", de);

    return params.toString();
}

// Fetch and render dashboard data
async function loadDashboard() {
    const qs = getFilterParams();
    const [monthlyRes, detailsRes] = await Promise.all([
        fetch("/api/dashboard/monthly?" + qs),
        fetch("/api/dashboard/details?" + qs)
    ]);

    const monthly = await monthlyRes.json();
    const details = await detailsRes.json();

    // Sort monthly data chronologically
    monthly.sort((a, b) => sortByMonth(a.production_date, b.production_date));

    renderLineChart(monthly);
    renderComboChart(monthly);
    renderRollupTable(monthly);
    renderRawTable(details);
}

// Reset filters
function resetFilters() {
    filterChoices.operator.removeActiveItems();
    filterChoices.property.removeActiveItems();
    filterChoices.category.removeActiveItems();
    document.getElementById("filter-date-start").value = "";
    document.getElementById("filter-date-end").value = "";
}

// Boot
document.addEventListener("DOMContentLoaded", async () => {
    // Load filter options
    const res = await fetch("/api/dashboard/filters");
    const options = await res.json();
    initFilters(options);

    // Wire up buttons
    document.getElementById("btn-apply-filters").addEventListener("click", loadDashboard);
    document.getElementById("btn-reset-filters").addEventListener("click", () => {
        resetFilters();
        loadDashboard();
    });

    // Initialize invoice tab
    initInvoiceTab();

    // Auto-load dashboard with no filters
    loadDashboard();
});
