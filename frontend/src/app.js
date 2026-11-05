import {
    addAuditEntry,
    createBusiness,
    getActiveBusiness,
    loadState,
    saveState,
    todayIso,
    uid
} from "./state.js";
import {
    buildReport,
    expenseTax,
    formatMoney,
    getClientHealthScore,
    getClientName,
    getDashboardMetrics,
    getExpenseBreakdown,
    getMonthlyRevenue,
    getSupplierName,
    invoiceTotals,
    monthKey,
    normalizeInvoiceStatus
} from "./calculations.js";
import { downloadCsv, downloadInvoicePdf } from "./exporters.js";

const appRoot = document.getElementById("app");
const modalRoot = document.getElementById("modalRoot");
const toastRoot = document.getElementById("toastRoot");

let state = loadState();
let ui = {
    view: "dashboard",
    invoiceSearch: "",
    invoiceStatus: "all",
    invoiceSort: "dueDate",
    expenseMonth: "all",
    expenseCategory: "all",
    expenseSort: "date-desc",
    contactType: "clients",
    contactSearch: "",
    reportType: "profitLoss"
};

saveState(state);

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    }[char]));
}

function activeBusiness() {
    return getActiveBusiness(state);
}

function persist(action, entity, details) {
    if (action && entity) {
        addAuditEntry(state, activeBusiness().id, action, entity, details);
    }
    saveState(state);
    renderApp();
}

function notify(message, type = "success") {
    toastRoot.className = "toast-stack";
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastRoot.appendChild(toast);
    setTimeout(() => toast.remove(), 3200);
}

function statusClass(value) {
    return String(value || "draft").toLowerCase().replace(/\s+/g, "-");
}

function labelText(value) {
    return String(value || "review-needed").replace(/-/g, " ");
}

function optionList(items, selectedId, fallback = "Unassigned") {
    const options = [`<option value="">${fallback}</option>`];
    for (const item of items) {
        const label = item.businessName || item.name;
        options.push(`<option value="${escapeHtml(item.id)}" ${item.id === selectedId ? "selected" : ""}>${escapeHtml(label)}</option>`);
    }
    return options.join("");
}

function openModal(title, bodyHtml, footerHtml = "") {
    modalRoot.innerHTML = `
        <div class="modal-backdrop" data-modal-close>
            <section class="modal" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}">
                <header class="modal-header">
                    <h2>${escapeHtml(title)}</h2>
                    <button class="button neutral small" type="button" data-modal-close>Close</button>
                </header>
                <div class="modal-body">${bodyHtml}</div>
                ${footerHtml ? `<footer class="modal-footer">${footerHtml}</footer>` : ""}
            </section>
        </div>
    `;
}

function closeModal() {
    modalRoot.innerHTML = "";
}

function confirmAction(title, message, onConfirm) {
    openModal(
        title,
        `<p>${escapeHtml(message)}</p>`,
        `
            <button class="button neutral" type="button" data-modal-close>Cancel</button>
            <button class="button danger" id="confirmActionButton" type="button">Delete</button>
        `
    );
    document.getElementById("confirmActionButton").addEventListener("click", () => {
        onConfirm();
        closeModal();
    });
}

function renderApp() {
    document.body.dataset.theme = state.theme || "light";
    const business = activeBusiness();
    const navItems = [
        ["dashboard", "Dashboard"],
        ["invoices", "Invoices"],
        ["expenses", "Expenses"],
        ["contacts", "Clients & Suppliers"],
        ["reports", "Reports"],
        ["audit", "Audit Trail"]
    ];

    appRoot.innerHTML = `
        <div class="app-shell">
            <aside class="sidebar">
                <div class="brand">
                    <strong>LedgerLite Assistant</strong>
                    <span>Bookkeeping control center</span>
                </div>
                <nav class="nav-list">
                    ${navItems.map(([key, label]) => `
                        <button class="nav-button ${ui.view === key ? "active" : ""}" type="button" data-nav="${key}">
                            <span>${label}</span>
                        </button>
                    `).join("")}
                </nav>
                <div class="sidebar-footer">
                    <strong>${escapeHtml(business.name)}</strong><br>
                    ${business.clients.length} clients, ${business.invoices.length} invoices
                </div>
            </aside>
            <div class="content-shell">
                <header class="topbar">
                    <label>
                        Business
                        <select id="businessSelect">
                            ${state.businesses.map((item) => `
                                <option value="${escapeHtml(item.id)}" ${item.id === business.id ? "selected" : ""}>${escapeHtml(item.name)}</option>
                            `).join("")}
                        </select>
                    </label>
                    <div class="topbar-actions">
                        <label>
                            Operator
                            <input id="operatorInput" value="${escapeHtml(state.currentUser || "")}" placeholder="Name">
                        </label>
                        <button class="button neutral" id="themeToggle" type="button">${state.theme === "dark" ? "Light Mode" : "Dark Mode"}</button>
                        <button class="button secondary" id="addBusinessButton" type="button">Add Business</button>
                    </div>
                </header>
                <main class="main-content">${renderView()}</main>
            </div>
        </div>
    `;
}

function renderView() {
    if (ui.view === "invoices") return renderInvoices();
    if (ui.view === "expenses") return renderExpenses();
    if (ui.view === "contacts") return renderContacts();
    if (ui.view === "reports") return renderReports();
    if (ui.view === "audit") return renderAudit();
    return renderDashboard();
}

function renderDashboard() {
    const business = activeBusiness();
    const metrics = getDashboardMetrics(business);
    const revenue = getMonthlyRevenue(business, 6);
    const maxRevenue = Math.max(...revenue.map((item) => item.total), 1);
    const categories = getExpenseBreakdown(business);
    const maxExpense = Math.max(...categories.map((item) => item.total), 1);
    const health = getClientHealthScore(business);

    return `
        <section class="page-heading">
            <span class="eyebrow">Financial Dashboard</span>
            <h1>${escapeHtml(business.name)}</h1>
            <p class="muted">Income, expenses, invoices, VAT, cash flow, and bookkeeping health in one place.</p>
        </section>
        <section class="grid cards">
            ${metricCard("Total Income", metrics.totalIncome, "good")}
            ${metricCard("Total Expenses", metrics.totalExpenses, "warn")}
            ${metricCard("Net Profit", metrics.netProfit, metrics.netProfit >= 0 ? "good" : "bad")}
            ${metricCard("Outstanding", metrics.outstandingInvoices, "warn")}
            ${metricCard("Overdue Invoices", `${metrics.overdueInvoices} (${formatMoney(metrics.overdueInvoiceTotal)})`, metrics.overdueInvoices ? "bad" : "good", false)}
            ${metricCard("Cash Flow This Month", metrics.cashFlowNet, metrics.cashFlowNet >= 0 ? "good" : "bad")}
            ${metricCard("VAT/Tax Estimate", metrics.taxEstimate, metrics.taxEstimate >= 0 ? "warn" : "good")}
            ${metricCard("Monthly Income", metrics.monthlyIncome, "good")}
        </section>
        <section class="grid two">
            <div class="panel">
                <div class="toolbar"><h2>Monthly Revenue</h2><span class="table-label">Paid invoices</span></div>
                <div class="chart">
                    ${revenue.map((item) => barRow(item.label, item.total, maxRevenue)).join("")}
                </div>
            </div>
            <div class="panel">
                <div class="toolbar"><h2>Client Health Score</h2><span class="table-label">${health.trend}</span></div>
                <div class="health-score">
                    <div class="score-ring" style="--score:${health.score}%"><strong>${health.score}</strong></div>
                    <div>
                        <p><strong>${health.overdueCount}</strong> overdue invoice(s)</p>
                        <p><strong>${health.missingExpenseInfo}</strong> expense record(s) need info</p>
                    </div>
                </div>
            </div>
        </section>
        <section class="grid two">
            <div class="panel">
                <div class="toolbar"><h2>Expense Categories</h2><span class="table-label">All expenses</span></div>
                ${categories.length ? `<div class="chart">${categories.map((item) => barRow(item.category, item.total, maxExpense)).join("")}</div>` : emptyState("No expenses recorded yet.")}
            </div>
            <div class="panel">
                <div class="toolbar"><h2>Cash Flow Summary</h2><span class="table-label">Current month</span></div>
                <div class="grid cards" style="grid-template-columns: repeat(3, 1fr);">
                    ${metricCard("Income", metrics.monthlyIncome, "good")}
                    ${metricCard("Expenses", metrics.monthlyExpenses, "warn")}
                    ${metricCard("Net", metrics.cashFlowNet, metrics.cashFlowNet >= 0 ? "good" : "bad")}
                </div>
            </div>
        </section>
    `;
}

function metricCard(label, value, tone = "", money = true) {
    const displayValue = money ? formatMoney(value) : value;
    return `
        <div class="card metric ${tone}">
            <span class="card-label">${escapeHtml(label)}</span>
            <strong>${escapeHtml(displayValue)}</strong>
        </div>
    `;
}

function barRow(label, value, maxValue) {
    const width = maxValue ? Math.max(4, (Number(value || 0) / maxValue) * 100) : 0;
    return `
        <div class="bar-row">
            <span>${escapeHtml(label)}</span>
            <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
            <strong>${formatMoney(value)}</strong>
        </div>
    `;
}

function emptyState(message) {
    return `<div class="empty-state"><p>${escapeHtml(message)}</p></div>`;
}

function filteredInvoices() {
    const business = activeBusiness();
    const query = ui.invoiceSearch.toLowerCase();
    let invoices = business.invoices.filter((invoice) => {
        const client = getClientName(business, invoice.clientId).toLowerCase();
        const matchesSearch = !query || invoice.number.toLowerCase().includes(query) || client.includes(query);
        const status = normalizeInvoiceStatus(invoice);
        const matchesStatus = ui.invoiceStatus === "all" || status === ui.invoiceStatus;
        return matchesSearch && matchesStatus;
    });

    invoices = [...invoices].sort((a, b) => {
        if (ui.invoiceSort === "total-desc") return invoiceTotals(b).total - invoiceTotals(a).total;
        if (ui.invoiceSort === "total-asc") return invoiceTotals(a).total - invoiceTotals(b).total;
        if (ui.invoiceSort === "date-desc") return String(b.issueDate).localeCompare(String(a.issueDate));
        return String(a.dueDate).localeCompare(String(b.dueDate));
    });
    return invoices;
}

function renderInvoices() {
    const invoices = filteredInvoices();
    return `
        <section class="page-heading">
            <span class="eyebrow">Invoice Management</span>
            <h1>Invoices</h1>
        </section>
        <section class="panel">
            <div class="toolbar">
                <div class="filters">
                    <input id="invoiceSearch" value="${escapeHtml(ui.invoiceSearch)}" placeholder="Search invoices or clients">
                    <select id="invoiceStatusFilter">
                        ${["all", "paid", "unpaid", "overdue"].map((status) => `<option value="${status}" ${ui.invoiceStatus === status ? "selected" : ""}>${status}</option>`).join("")}
                    </select>
                    <select id="invoiceSort">
                        <option value="dueDate" ${ui.invoiceSort === "dueDate" ? "selected" : ""}>Due date</option>
                        <option value="date-desc" ${ui.invoiceSort === "date-desc" ? "selected" : ""}>Newest</option>
                        <option value="total-desc" ${ui.invoiceSort === "total-desc" ? "selected" : ""}>Highest total</option>
                        <option value="total-asc" ${ui.invoiceSort === "total-asc" ? "selected" : ""}>Lowest total</option>
                    </select>
                </div>
                <button class="button" id="addInvoiceButton" type="button">Create Invoice</button>
            </div>
            ${invoices.length ? invoiceTable(invoices) : emptyState("No invoices match the current filters.")}
        </section>
    `;
}

function invoiceTable(invoices) {
    const business = activeBusiness();
    return `
        <div class="table-wrap">
            <table>
                <thead><tr><th>Invoice</th><th>Client</th><th>Due</th><th>Status</th><th>Label</th><th>Total</th><th>Actions</th></tr></thead>
                <tbody>
                    ${invoices.map((invoice) => {
                        const status = normalizeInvoiceStatus(invoice);
                        return `
                            <tr>
                                <td><strong>${escapeHtml(invoice.number)}</strong><br><span class="muted">${escapeHtml(invoice.issueDate)}</span></td>
                                <td>${escapeHtml(getClientName(business, invoice.clientId))}</td>
                                <td>${escapeHtml(invoice.dueDate || "")}</td>
                                <td><span class="status-pill ${statusClass(status)}">${escapeHtml(status)}</span></td>
                                <td><span class="status-pill ${statusClass(invoice.label)}">${escapeHtml(labelText(invoice.label))}</span></td>
                                <td><strong>${formatMoney(invoiceTotals(invoice).total)}</strong></td>
                                <td>
                                    <div class="table-actions">
                                        <button class="button small neutral" data-action="edit-invoice" data-id="${invoice.id}">Edit</button>
                                        <button class="button small" data-action="mark-paid" data-id="${invoice.id}">Paid</button>
                                        <button class="button small warning" data-action="mark-unpaid" data-id="${invoice.id}">Unpaid</button>
                                        <button class="button small danger" data-action="mark-overdue" data-id="${invoice.id}">Overdue</button>
                                        <button class="button small secondary" data-action="invoice-pdf" data-id="${invoice.id}">PDF</button>
                                        <button class="button small danger" data-action="delete-invoice" data-id="${invoice.id}">Delete</button>
                                    </div>
                                </td>
                            </tr>
                        `;
                    }).join("")}
                </tbody>
            </table>
        </div>
    `;
}

function filteredExpenses() {
    const business = activeBusiness();
    let expenses = business.expenses.filter((expense) => {
        const monthMatches = ui.expenseMonth === "all" || monthKey(expense.date) === ui.expenseMonth;
        const categoryMatches = ui.expenseCategory === "all" || expense.category === ui.expenseCategory;
        return monthMatches && categoryMatches;
    });
    expenses = [...expenses].sort((a, b) => {
        if (ui.expenseSort === "amount-desc") return Number(b.amount) - Number(a.amount);
        if (ui.expenseSort === "amount-asc") return Number(a.amount) - Number(b.amount);
        return String(b.date).localeCompare(String(a.date));
    });
    return expenses;
}

function renderExpenses() {
    const business = activeBusiness();
    const expenses = filteredExpenses();
    const categories = [...new Set(business.expenses.map((expense) => expense.category).filter(Boolean))].sort();
    const months = [...new Set(business.expenses.map((expense) => monthKey(expense.date)).filter(Boolean))].sort().reverse();
    const deductibleTotal = business.expenses.filter((expense) => expense.deductible).reduce((total, expense) => total + Number(expense.amount || 0), 0);
    const deductibleTax = business.expenses.filter((expense) => expense.deductible).reduce((total, expense) => total + expenseTax(expense), 0);

    return `
        <section class="page-heading">
            <span class="eyebrow">Expense Tracking</span>
            <h1>Expenses</h1>
        </section>
        <section class="grid cards">
            ${metricCard("Deductible Expenses", deductibleTotal, "good")}
            ${metricCard("Input VAT", deductibleTax, "good")}
            ${metricCard("Total Expenses", business.expenses.reduce((total, expense) => total + Number(expense.amount || 0), 0), "warn")}
            ${metricCard("Missing Receipts", business.expenses.filter((expense) => expense.deductible && !expense.receiptName).length, "bad", false)}
        </section>
        <section class="panel">
            <div class="toolbar">
                <div class="filters">
                    <select id="expenseMonthFilter"><option value="all">All months</option>${months.map((month) => `<option value="${month}" ${ui.expenseMonth === month ? "selected" : ""}>${month}</option>`).join("")}</select>
                    <select id="expenseCategoryFilter"><option value="all">All categories</option>${categories.map((category) => `<option value="${escapeHtml(category)}" ${ui.expenseCategory === category ? "selected" : ""}>${escapeHtml(category)}</option>`).join("")}</select>
                    <select id="expenseSort"><option value="date-desc" ${ui.expenseSort === "date-desc" ? "selected" : ""}>Newest</option><option value="amount-desc" ${ui.expenseSort === "amount-desc" ? "selected" : ""}>Highest amount</option><option value="amount-asc" ${ui.expenseSort === "amount-asc" ? "selected" : ""}>Lowest amount</option></select>
                </div>
                <button class="button" id="addExpenseButton" type="button">Add Expense</button>
            </div>
            ${expenses.length ? expenseTable(expenses) : emptyState("No expenses match the current filters.")}
        </section>
    `;
}

function expenseTable(expenses) {
    const business = activeBusiness();
    return `
        <div class="table-wrap">
            <table>
                <thead><tr><th>Date</th><th>Supplier</th><th>Category</th><th>Amount</th><th>Tax</th><th>Label</th><th>Receipt</th><th>Actions</th></tr></thead>
                <tbody>
                    ${expenses.map((expense) => `
                        <tr>
                            <td>${escapeHtml(expense.date)}</td>
                            <td>${escapeHtml(getSupplierName(business, expense.supplierId))}</td>
                            <td>${escapeHtml(expense.category || "Uncategorised")}</td>
                            <td><strong>${formatMoney(expense.amount)}</strong><br><span class="muted">${expense.paymentMethod || ""}</span></td>
                            <td>${formatMoney(expenseTax(expense))}</td>
                            <td><span class="status-pill ${statusClass(expense.label)}">${escapeHtml(labelText(expense.label))}</span></td>
                            <td>${expense.receiptName ? escapeHtml(expense.receiptName) : "<span class='muted'>Missing</span>"}</td>
                            <td>
                                <div class="table-actions">
                                    <button class="button small neutral" data-action="edit-expense" data-id="${expense.id}">Edit</button>
                                    <button class="button small danger" data-action="delete-expense" data-id="${expense.id}">Delete</button>
                                </div>
                            </td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;
}

function renderContacts() {
    const business = activeBusiness();
    const type = ui.contactType;
    const records = business[type].filter((item) => {
        const query = ui.contactSearch.toLowerCase();
        return !query || [item.name, item.businessName, item.email, item.taxNumber].some((value) => String(value || "").toLowerCase().includes(query));
    });

    return `
        <section class="page-heading">
            <span class="eyebrow">Client & Supplier Management</span>
            <h1>Contacts</h1>
        </section>
        <section class="panel">
            <div class="toolbar">
                <div class="filters">
                    <select id="contactTypeFilter"><option value="clients" ${type === "clients" ? "selected" : ""}>Clients</option><option value="suppliers" ${type === "suppliers" ? "selected" : ""}>Suppliers</option></select>
                    <input id="contactSearch" value="${escapeHtml(ui.contactSearch)}" placeholder="Search contacts">
                </div>
                <button class="button" id="addContactButton" type="button">Add ${type === "clients" ? "Client" : "Supplier"}</button>
            </div>
            ${records.length ? contactTable(records, type) : emptyState(`No ${type} found.`)}
        </section>
    `;
}

function contactTable(records, type) {
    return `
        <div class="table-wrap">
            <table>
                <thead><tr><th>Name</th><th>Business</th><th>Email</th><th>Phone</th><th>Tax/VAT</th><th>Address</th><th>Actions</th></tr></thead>
                <tbody>
                    ${records.map((record) => `
                        <tr>
                            <td><strong>${escapeHtml(record.name)}</strong></td>
                            <td>${escapeHtml(record.businessName || "")}</td>
                            <td>${escapeHtml(record.email || "")}</td>
                            <td>${escapeHtml(record.phone || "")}</td>
                            <td>${escapeHtml(record.taxNumber || "")}</td>
                            <td>${escapeHtml(record.address || "")}</td>
                            <td>
                                <div class="table-actions">
                                    <button class="button small neutral" data-action="edit-contact" data-type="${type}" data-id="${record.id}">Edit</button>
                                    <button class="button small danger" data-action="delete-contact" data-type="${type}" data-id="${record.id}">Delete</button>
                                </div>
                            </td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;
}

function renderReports() {
    const report = buildReport(activeBusiness(), ui.reportType);
    const reports = [
        ["profitLoss", "Profit & Loss"],
        ["sales", "Sales"],
        ["expenses", "Expenses"],
        ["tax", "Tax/VAT"],
        ["cashflow", "Cash Flow"]
    ];
    return `
        <section class="page-heading">
            <span class="eyebrow">Reports Section</span>
            <h1>${escapeHtml(report.title)}</h1>
        </section>
        <section class="panel">
            <div class="toolbar">
                <div class="filters">
                    ${reports.map(([type, label]) => `<button class="button ${ui.reportType === type ? "" : "neutral"}" data-report-type="${type}" type="button">${label}</button>`).join("")}
                </div>
                <button class="button secondary" id="exportReportButton" type="button">Export CSV</button>
            </div>
            ${reportTable(report)}
        </section>
    `;
}

function reportTable(report) {
    return `
        <div class="table-wrap">
            <table>
                <thead><tr>${report.headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead>
                <tbody>
                    ${report.rows.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")}
                </tbody>
            </table>
        </div>
    `;
}

function renderAudit() {
    const logs = activeBusiness().auditLog || [];
    return `
        <section class="page-heading">
            <span class="eyebrow">Accountant-Friendly Features</span>
            <h1>Audit Trail</h1>
        </section>
        <section class="panel">
            ${logs.length ? `
                <div class="table-wrap">
                    <table>
                        <thead><tr><th>Timestamp</th><th>User</th><th>Action</th><th>Entity</th><th>Details</th></tr></thead>
                        <tbody>
                            ${logs.map((log) => `
                                <tr>
                                    <td>${new Date(log.timestamp).toLocaleString()}</td>
                                    <td>${escapeHtml(log.user)}</td>
                                    <td>${escapeHtml(log.action)}</td>
                                    <td>${escapeHtml(log.entity)}</td>
                                    <td>${escapeHtml(log.details)}</td>
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                </div>
            ` : emptyState("No audit actions yet.")}
        </section>
    `;
}

function showBusinessForm() {
    openModal(
        "Add Business",
        `
            <form id="businessForm" class="grid">
                <label>Business Name<input name="name" required placeholder="Client or business name"></label>
                <label>Owner<input name="owner" placeholder="Owner or contact"></label>
                <label>VAT/Tax Rate<input name="taxRate" type="number" step="0.01" value="15"></label>
            </form>
        `,
        `<button class="button neutral" type="button" data-modal-close>Cancel</button><button class="button" form="businessForm" type="submit">Save Business</button>`
    );
    document.getElementById("businessForm").addEventListener("submit", (event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const business = createBusiness(form.get("name") || "New Business");
        business.owner = form.get("owner") || "";
        business.taxRate = Number(form.get("taxRate") || 15);
        state.businesses.push(business);
        state.activeBusinessId = business.id;
        persist("created", "business", business.name);
        closeModal();
        notify("Business added.");
    });
}

function showContactForm(type, id = null) {
    const business = activeBusiness();
    const records = business[type];
    const record = records.find((item) => item.id === id) || {};
    const title = `${id ? "Edit" : "Add"} ${type === "clients" ? "Client" : "Supplier"}`;
    openModal(
        title,
        `
            <form id="contactForm" class="field-grid">
                <label>Name<input name="name" required value="${escapeHtml(record.name || "")}"></label>
                <label>Business Name<input name="businessName" value="${escapeHtml(record.businessName || "")}"></label>
                <label>Email<input name="email" type="email" value="${escapeHtml(record.email || "")}"></label>
                <label>Phone<input name="phone" value="${escapeHtml(record.phone || "")}"></label>
                <label>Tax/VAT Number<input name="taxNumber" value="${escapeHtml(record.taxNumber || "")}"></label>
                <label>Address<textarea name="address">${escapeHtml(record.address || "")}</textarea></label>
            </form>
        `,
        `<button class="button neutral" type="button" data-modal-close>Cancel</button><button class="button" form="contactForm" type="submit">Save</button>`
    );
    document.getElementById("contactForm").addEventListener("submit", (event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const payload = {
            id: id || uid(type === "clients" ? "client" : "supplier"),
            name: form.get("name"),
            businessName: form.get("businessName"),
            email: form.get("email"),
            phone: form.get("phone"),
            taxNumber: form.get("taxNumber"),
            address: form.get("address"),
            createdAt: record.createdAt || new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };
        if (id) {
            records.splice(records.findIndex((item) => item.id === id), 1, payload);
        } else {
            records.push(payload);
        }
        persist(id ? "edited" : "created", type.slice(0, -1), payload.name);
        closeModal();
        notify(`${type === "clients" ? "Client" : "Supplier"} saved.`);
    });
}

function showExpenseForm(id = null) {
    const business = activeBusiness();
    const expense = business.expenses.find((item) => item.id === id) || {
        date: todayIso(),
        taxRate: business.taxRate,
        deductible: true,
        label: "review-needed"
    };
    openModal(
        id ? "Edit Expense" : "Add Expense",
        `
            <form id="expenseForm" class="field-grid">
                <label>Date<input name="date" type="date" required value="${escapeHtml(expense.date)}"></label>
                <label>Supplier<select name="supplierId">${optionList(business.suppliers, expense.supplierId, "No supplier")}</select></label>
                <label>Category<input name="category" required value="${escapeHtml(expense.category || "")}" placeholder="Software, Rent, Travel"></label>
                <label>Amount<input name="amount" type="number" step="0.01" min="0" required value="${escapeHtml(expense.amount || "")}"></label>
                <label>VAT/Tax %<input name="taxRate" type="number" step="0.01" min="0" value="${escapeHtml(expense.taxRate ?? business.taxRate)}"></label>
                <label>Payment Method<input name="paymentMethod" value="${escapeHtml(expense.paymentMethod || "")}" placeholder="EFT, Cash, Card"></label>
                <label>Status Label<select name="label">${statusLabelOptions(expense.label)}</select></label>
                <label>Receipt Placeholder<input name="receipt" type="file" accept="image/*,.pdf"></label>
                <label><span>Deductible</span><select name="deductible"><option value="true" ${expense.deductible ? "selected" : ""}>Yes</option><option value="false" ${!expense.deductible ? "selected" : ""}>No</option></select></label>
                <label>Notes<textarea name="notes">${escapeHtml(expense.notes || "")}</textarea></label>
                <label>Comments<textarea name="comments">${escapeHtml(expense.comments || "")}</textarea></label>
            </form>
        `,
        `<button class="button neutral" type="button" data-modal-close>Cancel</button><button class="button" form="expenseForm" type="submit">Save Expense</button>`
    );
    document.getElementById("expenseForm").addEventListener("submit", (event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const receipt = event.currentTarget.elements.receipt.files[0];
        const payload = {
            ...expense,
            id: id || uid("exp"),
            date: form.get("date"),
            supplierId: form.get("supplierId"),
            category: form.get("category"),
            amount: Number(form.get("amount") || 0),
            taxRate: Number(form.get("taxRate") || 0),
            paymentMethod: form.get("paymentMethod"),
            label: form.get("label"),
            receiptName: receipt?.name || expense.receiptName || "",
            deductible: form.get("deductible") === "true",
            notes: form.get("notes"),
            comments: form.get("comments"),
            createdBy: expense.createdBy || state.currentUser || "Unknown",
            createdAt: expense.createdAt || new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };
        if (id) {
            business.expenses.splice(business.expenses.findIndex((item) => item.id === id), 1, payload);
        } else {
            business.expenses.push(payload);
        }
        persist(id ? "edited" : "created", "expense", `${payload.category} ${formatMoney(payload.amount)}`);
        closeModal();
        notify("Expense saved.");
    });
}

function statusLabelOptions(selected) {
    return ["review-needed", "approved", "missing-info", "draft"].map((label) => {
        return `<option value="${label}" ${selected === label ? "selected" : ""}>${labelText(label)}</option>`;
    }).join("");
}

function showInvoiceForm(id = null) {
    const business = activeBusiness();
    const invoice = business.invoices.find((item) => item.id === id) || {
        number: `INV-${String(business.invoices.length + 1001).padStart(4, "0")}`,
        issueDate: todayIso(),
        dueDate: todayIso(),
        status: "unpaid",
        label: "review-needed",
        items: [{ description: "", quantity: 1, price: 0, taxRate: business.taxRate }]
    };
    let draftItems = (invoice.items || []).map((item) => ({ ...item }));

    openModal(
        id ? "Edit Invoice" : "Create Invoice",
        `
            <form id="invoiceForm" class="grid">
                <div class="field-grid">
                    <label>Client<select name="clientId">${optionList(business.clients, invoice.clientId, "No client")}</select></label>
                    <label>Invoice Number<input name="number" required value="${escapeHtml(invoice.number)}"></label>
                    <label>Issue Date<input name="issueDate" type="date" required value="${escapeHtml(invoice.issueDate)}"></label>
                    <label>Due Date<input name="dueDate" type="date" required value="${escapeHtml(invoice.dueDate)}"></label>
                    <label>Status<select name="status"><option value="unpaid" ${invoice.status === "unpaid" ? "selected" : ""}>Unpaid</option><option value="paid" ${invoice.status === "paid" ? "selected" : ""}>Paid</option><option value="overdue" ${invoice.status === "overdue" ? "selected" : ""}>Overdue</option></select></label>
                    <label>Status Label<select name="label">${statusLabelOptions(invoice.label)}</select></label>
                </div>
                <div>
                    <div class="toolbar"><h2>Items</h2><button class="button small secondary" id="addInvoiceItemButton" type="button">Add Item</button></div>
                    <div id="invoiceItems" class="grid"></div>
                </div>
                <div class="grid cards" style="grid-template-columns: repeat(3, 1fr);" id="invoiceTotalsPreview"></div>
                <div class="field-grid">
                    <label>Notes<textarea name="notes">${escapeHtml(invoice.notes || "")}</textarea></label>
                    <label>Comments<textarea name="comments">${escapeHtml(invoice.comments || "")}</textarea></label>
                </div>
            </form>
        `,
        `<button class="button neutral" type="button" data-modal-close>Cancel</button><button class="button" form="invoiceForm" type="submit">Save Invoice</button>`
    );

    const form = document.getElementById("invoiceForm");
    const itemsRoot = document.getElementById("invoiceItems");
    const totalsRoot = document.getElementById("invoiceTotalsPreview");

    function syncItemsFromDom() {
        draftItems = [...itemsRoot.querySelectorAll("[data-line-item]")].map((row) => ({
            description: row.querySelector("[name='itemDescription']").value,
            quantity: Number(row.querySelector("[name='itemQuantity']").value || 0),
            price: Number(row.querySelector("[name='itemPrice']").value || 0),
            taxRate: Number(row.querySelector("[name='itemTax']").value || 0)
        }));
    }

    function renderItems() {
        itemsRoot.innerHTML = draftItems.map((item, index) => `
            <div class="line-item-grid" data-line-item="${index}">
                <label>Description<input name="itemDescription" required value="${escapeHtml(item.description || "")}"></label>
                <label>Qty<input name="itemQuantity" type="number" min="0" step="0.01" value="${escapeHtml(item.quantity ?? 1)}"></label>
                <label>Price<input name="itemPrice" type="number" min="0" step="0.01" value="${escapeHtml(item.price ?? 0)}"></label>
                <label>VAT %<input name="itemTax" type="number" min="0" step="0.01" value="${escapeHtml(item.taxRate ?? business.taxRate)}"></label>
                <button class="button small danger" type="button" data-remove-line="${index}">Remove</button>
            </div>
        `).join("");
        renderTotalsPreview();
    }

    function renderTotalsPreview() {
        const totals = invoiceTotals({ items: draftItems });
        totalsRoot.innerHTML = `
            ${metricCard("Subtotal", totals.subtotal)}
            ${metricCard("VAT/Tax", totals.tax, "warn")}
            ${metricCard("Total", totals.total, "good")}
        `;
    }

    form.addEventListener("input", () => {
        syncItemsFromDom();
        renderTotalsPreview();
    });
    document.getElementById("addInvoiceItemButton").addEventListener("click", () => {
        syncItemsFromDom();
        draftItems.push({ description: "", quantity: 1, price: 0, taxRate: business.taxRate });
        renderItems();
    });
    itemsRoot.addEventListener("click", (event) => {
        const button = event.target.closest("[data-remove-line]");
        if (!button) return;
        syncItemsFromDom();
        draftItems.splice(Number(button.dataset.removeLine), 1);
        if (!draftItems.length) draftItems.push({ description: "", quantity: 1, price: 0, taxRate: business.taxRate });
        renderItems();
    });
    form.addEventListener("submit", (event) => {
        event.preventDefault();
        syncItemsFromDom();
        const data = new FormData(form);
        const payload = {
            ...invoice,
            id: id || uid("inv"),
            clientId: data.get("clientId"),
            number: data.get("number"),
            issueDate: data.get("issueDate"),
            dueDate: data.get("dueDate"),
            status: data.get("status"),
            label: data.get("label"),
            notes: data.get("notes"),
            comments: data.get("comments"),
            items: draftItems.filter((item) => item.description || item.price),
            createdBy: invoice.createdBy || state.currentUser || "Unknown",
            createdAt: invoice.createdAt || new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            paidAt: data.get("status") === "paid" ? (invoice.paidAt || todayIso()) : ""
        };
        if (id) {
            business.invoices.splice(business.invoices.findIndex((item) => item.id === id), 1, payload);
        } else {
            business.invoices.push(payload);
        }
        persist(id ? "edited" : "created", "invoice", payload.number);
        closeModal();
        notify("Invoice saved.");
    });
    renderItems();
}

function handleClick(event) {
    const nav = event.target.closest("[data-nav]");
    if (nav) {
        ui.view = nav.dataset.nav;
        renderApp();
        return;
    }

    if (event.target.closest("#themeToggle")) {
        state.theme = state.theme === "dark" ? "light" : "dark";
        persist();
        return;
    }

    if (event.target.closest("#addBusinessButton")) return showBusinessForm();
    if (event.target.closest("#addInvoiceButton")) return showInvoiceForm();
    if (event.target.closest("#addExpenseButton")) return showExpenseForm();
    if (event.target.closest("#addContactButton")) return showContactForm(ui.contactType);
    if (event.target.closest("#exportReportButton")) {
        downloadCsv(buildReport(activeBusiness(), ui.reportType));
        notify("Report CSV exported.");
        return;
    }

    const reportButton = event.target.closest("[data-report-type]");
    if (reportButton) {
        ui.reportType = reportButton.dataset.reportType;
        renderApp();
        return;
    }

    const actionButton = event.target.closest("[data-action]");
    if (!actionButton) return;
    const { action, id, type } = actionButton.dataset;
    const business = activeBusiness();

    if (action === "edit-invoice") return showInvoiceForm(id);
    if (action === "edit-expense") return showExpenseForm(id);
    if (action === "edit-contact") return showContactForm(type, id);
    if (action === "invoice-pdf") {
        const invoice = business.invoices.find((item) => item.id === id);
        if (invoice) {
            downloadInvoicePdf(invoice, business);
            notify("Invoice PDF downloaded.");
        }
        return;
    }
    if (action === "mark-paid" || action === "mark-unpaid" || action === "mark-overdue") {
        const invoice = business.invoices.find((item) => item.id === id);
        if (invoice) {
            invoice.status = action === "mark-paid" ? "paid" : action === "mark-overdue" ? "overdue" : "unpaid";
            invoice.paidAt = action === "mark-paid" ? todayIso() : "";
            invoice.updatedAt = new Date().toISOString();
            persist("updated status", "invoice", `${invoice.number} marked ${invoice.status}`);
            notify(`Invoice marked ${invoice.status}.`);
        }
        return;
    }
    if (action === "delete-invoice") {
        const invoice = business.invoices.find((item) => item.id === id);
        confirmAction("Delete Invoice", `Delete invoice ${invoice?.number || ""}?`, () => {
            business.invoices = business.invoices.filter((item) => item.id !== id);
            persist("deleted", "invoice", invoice?.number || id);
            notify("Invoice deleted.");
        });
        return;
    }
    if (action === "delete-expense") {
        const expense = business.expenses.find((item) => item.id === id);
        confirmAction("Delete Expense", `Delete expense ${expense?.category || ""}?`, () => {
            business.expenses = business.expenses.filter((item) => item.id !== id);
            persist("deleted", "expense", expense?.category || id);
            notify("Expense deleted.");
        });
        return;
    }
    if (action === "delete-contact") {
        const record = business[type].find((item) => item.id === id);
        confirmAction("Delete Contact", `Delete ${record?.name || "contact"}?`, () => {
            business[type] = business[type].filter((item) => item.id !== id);
            persist("deleted", type.slice(0, -1), record?.name || id);
            notify("Contact deleted.");
        });
    }
}

function handleChange(event) {
    if (event.target.id === "businessSelect") {
        state.activeBusinessId = event.target.value;
        persist();
        return;
    }
    if (event.target.id === "invoiceStatusFilter") ui.invoiceStatus = event.target.value;
    if (event.target.id === "invoiceSort") ui.invoiceSort = event.target.value;
    if (event.target.id === "expenseMonthFilter") ui.expenseMonth = event.target.value;
    if (event.target.id === "expenseCategoryFilter") ui.expenseCategory = event.target.value;
    if (event.target.id === "expenseSort") ui.expenseSort = event.target.value;
    if (event.target.id === "contactTypeFilter") ui.contactType = event.target.value;
    if (event.target.id === "invoiceSearch") ui.invoiceSearch = event.target.value;
    if (event.target.id === "contactSearch") ui.contactSearch = event.target.value;
    renderApp();
}

function handleInput(event) {
    if (event.target.id === "operatorInput") {
        state.currentUser = event.target.value;
        saveState(state);
        return;
    }
}

modalRoot.addEventListener("click", (event) => {
    if (event.target.dataset.modalClose !== undefined) {
        closeModal();
    }
});

appRoot.addEventListener("click", handleClick);
appRoot.addEventListener("change", handleChange);
appRoot.addEventListener("input", handleInput);

renderApp();
