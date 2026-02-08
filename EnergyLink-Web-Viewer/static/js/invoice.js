/**
 * Invoice generator: cascading filters (date -> operator -> invoice),
 * rendering, and print.
 */

let invoiceOperatorChoices = null;
let invoiceSelectChoices = null;
let allInvoices = [];
let selectedDateMonths = 0; // 0 = All

async function initInvoiceTab() {
    const res = await fetch("/api/invoices/");
    allInvoices = await res.json();

    // Init operator dropdown (single-select via maxItemCount)
    invoiceOperatorChoices = new Choices("#invoice-operator-select", {
        removeItemButton: true,
        maxItemCount: 1,
        placeholderValue: "All operators",
        searchPlaceholderValue: "Search...",
        shouldSort: true,
    });

    // Init invoice dropdown (single-select via maxItemCount)
    invoiceSelectChoices = new Choices("#invoice-select", {
        removeItemButton: true,
        maxItemCount: 1,
        placeholderValue: "Select an invoice...",
        searchPlaceholderValue: "Search...",
        shouldSort: false,
    });

    // Wire date preset buttons
    document.querySelectorAll("#invoice-date-presets button").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll("#invoice-date-presets button").forEach(b =>
                b.classList.remove("active"));
            btn.classList.add("active");
            selectedDateMonths = parseInt(btn.dataset.months, 10);
            updateOperatorDropdown();
        });
    });

    // Wire operator change -> update invoice list
    document.getElementById("invoice-operator-select").addEventListener("change", () => {
        updateInvoiceDropdown();
    });

    // Wire invoice selection -> render
    document.getElementById("invoice-select").addEventListener("change", async (e) => {
        const id = e.detail?.value || e.target.value;
        if (!id) return;
        await loadInvoice(id);
    });

    // Print button
    document.getElementById("btn-print-invoice").addEventListener("click", () => {
        window.print();
    });

    // Initial population
    updateOperatorDropdown();
}

function getDateCutoff(months) {
    if (!months) return null;
    const now = new Date();
    now.setMonth(now.getMonth() - months);
    return now;
}

function parseInvoiceDate(dateStr) {
    if (!dateStr) return null;
    return new Date(dateStr);
}

function getFilteredInvoices() {
    let filtered = allInvoices;

    // Date filter
    if (selectedDateMonths > 0) {
        const cutoff = getDateCutoff(selectedDateMonths);
        filtered = filtered.filter(inv => {
            const d = parseInvoiceDate(inv.invoice_date);
            return d && d >= cutoff;
        });
    }

    return filtered;
}

function updateOperatorDropdown() {
    const filtered = getFilteredInvoices();

    // Get distinct operators from filtered invoices
    const operators = [...new Set(filtered.map(inv => inv.operator))].sort();

    invoiceOperatorChoices.clearStore();
    invoiceOperatorChoices.setChoices(
        [{ value: "", label: "All operators", placeholder: true },
         ...operators.map(o => ({ value: o, label: o }))],
        "value", "label", true
    );

    // Clear invoice content
    document.getElementById("invoice-content").innerHTML = "";
    document.getElementById("btn-print-invoice").disabled = true;

    updateInvoiceDropdown();
}

function updateInvoiceDropdown() {
    let filtered = getFilteredInvoices();

    // Operator filter
    const selectedOp = invoiceOperatorChoices.getValue(true);
    const op = Array.isArray(selectedOp) ? selectedOp[0] : selectedOp;
    if (op) {
        filtered = filtered.filter(inv => inv.operator === op);
    }

    const choices = filtered.map(inv => ({
        value: String(inv.invoice_id),
        label: `${inv.operator} - Chk #${inv.check_number} - ${inv.invoice_date} ($${Number(inv.total_amount).toFixed(2)})`,
    }));

    invoiceSelectChoices.clearStore();
    invoiceSelectChoices.setChoices(
        [{ value: "", label: "Select an invoice...", placeholder: true },
         ...choices],
        "value", "label", true
    );

    // Clear invoice content
    document.getElementById("invoice-content").innerHTML = "";
    document.getElementById("btn-print-invoice").disabled = true;
}

async function loadInvoice(invoiceId) {
    const res = await fetch(`/api/invoices/${invoiceId}`);
    if (!res.ok) {
        document.getElementById("invoice-content").innerHTML =
            '<div class="alert alert-danger">Invoice not found.</div>';
        return;
    }

    const inv = await res.json();
    document.getElementById("btn-print-invoice").disabled = false;
    renderInvoice(inv);
}

function fmtMoney(val) {
    if (val === null || val === undefined) return "$0.00";
    const n = Number(val);
    const neg = n < 0;
    const abs = Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return neg ? `($${abs})` : `$${abs}`;
}

function renderInvoice(inv) {
    const container = document.getElementById("invoice-content");

    let html = `
        <div class="invoice-page">
            <div class="invoice-header">
                <div class="row">
                    <div class="col-8">
                        <h3 class="mb-1">${inv.operator}</h3>
                        <p class="text-muted mb-0">Owner #: ${inv.owner_number}</p>
                    </div>
                    <div class="col-4 text-end">
                        <h5>Revenue Statement</h5>
                        <p class="mb-0">Check #: <strong>${inv.check_number}</strong></p>
                        <p class="mb-0">Date: ${inv.invoice_date}</p>
                        <p class="mb-0">Acct Month: ${inv.op_acct_month}</p>
                    </div>
                </div>
            </div>

            <hr>

            <div class="invoice-summary">
                <div class="row">
                    <div class="col-3 text-center">
                        <div class="fw-semibold">Revenue</div>
                        <div class="fs-5">${fmtMoney(inv.total_revenue)}</div>
                    </div>
                    <div class="col-3 text-center">
                        <div class="fw-semibold">Tax</div>
                        <div class="fs-5">${fmtMoney(inv.total_tax)}</div>
                    </div>
                    <div class="col-3 text-center">
                        <div class="fw-semibold">Deductions</div>
                        <div class="fs-5">${fmtMoney(inv.total_deductions)}</div>
                    </div>
                    <div class="col-3 text-center">
                        <div class="fw-semibold">Net Amount</div>
                        <div class="fs-4 fw-bold">${fmtMoney(inv.total_amount)}</div>
                    </div>
                </div>
            </div>

            <hr>
    `;

    // Properties
    if (inv.properties && inv.properties.length) {
        inv.properties.forEach(prop => {
            html += `
                <div class="property-section mb-4">
                    <h6 class="bg-light p-2 border">
                        ${prop.description}
                        <span class="float-end">Total: ${fmtMoney(prop.total)}</span>
                    </h6>
                    <div class="row mb-2 small text-muted px-2">
                        <div class="col-3">Cost Center: ${prop.cost_center || ""}</div>
                        <div class="col-3">${prop.state || ""}, ${prop.county || ""}</div>
                        <div class="col-2">Revenue: ${fmtMoney(prop.owner_share_revenue)}</div>
                        <div class="col-2">Tax: ${fmtMoney(prop.tax)}</div>
                        <div class="col-2">Deductions: ${fmtMoney(prop.deductions)}</div>
                    </div>
            `;

            if (prop.details && prop.details.length) {
                html += `
                    <table class="table table-sm table-bordered small">
                        <thead class="table-light">
                            <tr>
                                <th>Category</th>
                                <th>Code</th>
                                <th>Type</th>
                                <th>Prod Date</th>
                                <th class="text-end">Volume</th>
                                <th class="text-end">Price</th>
                                <th class="text-end">Value</th>
                                <th class="text-end">Owner %</th>
                                <th class="text-end">Owner Vol</th>
                                <th class="text-end">Owner Value</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                prop.details.forEach(d => {
                    const rowClass = (d.type_description === "ROYALTY INTEREST" || d.type_description === "RI")
                        ? "" : "text-danger";
                    html += `
                        <tr class="${rowClass}">
                            <td>${d.product_category || ""}</td>
                            <td>${d.code || ""}</td>
                            <td>${d.type_description || ""}</td>
                            <td>${d.production_date || ""}</td>
                            <td class="text-end">${d.property_volume != null ? Number(d.property_volume).toFixed(2) : ""}</td>
                            <td class="text-end">${d.property_price != null ? Number(d.property_price).toFixed(4) : ""}</td>
                            <td class="text-end">${fmtMoney(d.property_value)}</td>
                            <td class="text-end">${d.owner_pct != null ? Number(d.owner_pct).toFixed(4) : ""}</td>
                            <td class="text-end">${d.owner_volume != null ? Number(d.owner_volume).toFixed(2) : ""}</td>
                            <td class="text-end">${fmtMoney(d.owner_value)}</td>
                        </tr>
                    `;
                });

                html += `
                        </tbody>
                    </table>
                `;
            }

            html += `</div>`;
        });
    }

    html += `</div>`;
    container.innerHTML = html;
}
