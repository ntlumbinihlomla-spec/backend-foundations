export const MONEY_FORMATTER = new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency: "ZAR",
    minimumFractionDigits: 2
});

export function formatMoney(value) {
    return MONEY_FORMATTER.format(Number(value || 0));
}

export function parseAmount(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
}

export function invoiceTotals(invoice) {
    const items = invoice.items || [];
    const subtotal = items.reduce((total, item) => {
        return total + parseAmount(item.quantity) * parseAmount(item.price);
    }, 0);
    const tax = items.reduce((total, item) => {
        const lineTotal = parseAmount(item.quantity) * parseAmount(item.price);
        return total + lineTotal * (parseAmount(item.taxRate) / 100);
    }, 0);
    return {
        subtotal,
        tax,
        total: subtotal + tax
    };
}

export function expenseTax(expense) {
    const amount = parseAmount(expense.amount);
    const taxRate = parseAmount(expense.taxRate);
    if (!taxRate) return 0;
    return amount - amount / (1 + taxRate / 100);
}

export function getClientName(business, clientId) {
    const client = business.clients.find((item) => item.id === clientId);
    return client?.businessName || client?.name || "Unassigned";
}

export function getSupplierName(business, supplierId) {
    const supplier = business.suppliers.find((item) => item.id === supplierId);
    return supplier?.businessName || supplier?.name || "Unassigned";
}

export function isOverdue(invoice, now = new Date()) {
    if (invoice.status === "paid") return false;
    if (!invoice.dueDate) return false;
    const dueDate = new Date(`${invoice.dueDate}T23:59:59`);
    return dueDate < now;
}

export function normalizeInvoiceStatus(invoice) {
    if (invoice.status === "paid") return "paid";
    return isOverdue(invoice) ? "overdue" : invoice.status || "unpaid";
}

export function monthKey(dateValue) {
    return String(dateValue || "").slice(0, 7);
}

export function currentMonthKey() {
    return new Date().toISOString().slice(0, 7);
}

export function monthLabel(key) {
    if (!key) return "Unknown";
    const [year, month] = key.split("-");
    return new Date(Number(year), Number(month) - 1, 1).toLocaleDateString("en-ZA", {
        month: "short",
        year: "2-digit"
    });
}

export function recentMonthKeys(count = 6) {
    const result = [];
    const date = new Date();
    date.setDate(1);
    for (let index = count - 1; index >= 0; index -= 1) {
        const item = new Date(date);
        item.setMonth(date.getMonth() - index);
        result.push(item.toISOString().slice(0, 7));
    }
    return result;
}

export function getDashboardMetrics(business) {
    const paidInvoices = business.invoices.filter((invoice) => normalizeInvoiceStatus(invoice) === "paid");
    const openInvoices = business.invoices.filter((invoice) => normalizeInvoiceStatus(invoice) !== "paid");
    const overdueInvoices = business.invoices.filter((invoice) => normalizeInvoiceStatus(invoice) === "overdue");
    const totalIncome = paidInvoices.reduce((total, invoice) => total + invoiceTotals(invoice).total, 0);
    const totalExpenses = business.expenses.reduce((total, expense) => total + parseAmount(expense.amount), 0);
    const outputTax = business.invoices.reduce((total, invoice) => total + invoiceTotals(invoice).tax, 0);
    const inputTax = business.expenses
        .filter((expense) => expense.deductible)
        .reduce((total, expense) => total + expenseTax(expense), 0);
    const outstandingInvoices = openInvoices.reduce((total, invoice) => total + invoiceTotals(invoice).total, 0);
    const overdueInvoiceTotal = overdueInvoices.reduce((total, invoice) => total + invoiceTotals(invoice).total, 0);
    const month = currentMonthKey();
    const monthlyIncome = paidInvoices
        .filter((invoice) => monthKey(invoice.paidAt || invoice.issueDate) === month)
        .reduce((total, invoice) => total + invoiceTotals(invoice).total, 0);
    const monthlyExpenses = business.expenses
        .filter((expense) => monthKey(expense.date) === month)
        .reduce((total, expense) => total + parseAmount(expense.amount), 0);

    return {
        totalIncome,
        totalExpenses,
        netProfit: totalIncome - totalExpenses,
        outstandingInvoices,
        overdueInvoices: overdueInvoices.length,
        overdueInvoiceTotal,
        cashFlowNet: monthlyIncome - monthlyExpenses,
        monthlyIncome,
        monthlyExpenses,
        taxEstimate: outputTax - inputTax,
        outputTax,
        inputTax
    };
}

export function getMonthlyRevenue(business, count = 6) {
    const keys = recentMonthKeys(count);
    return keys.map((key) => {
        const total = business.invoices
            .filter((invoice) => normalizeInvoiceStatus(invoice) === "paid")
            .filter((invoice) => monthKey(invoice.paidAt || invoice.issueDate) === key)
            .reduce((sum, invoice) => sum + invoiceTotals(invoice).total, 0);
        return { key, label: monthLabel(key), total };
    });
}

export function getExpenseBreakdown(business) {
    const categories = new Map();
    for (const expense of business.expenses) {
        const category = expense.category || "Uncategorised";
        categories.set(category, (categories.get(category) || 0) + parseAmount(expense.amount));
    }
    return [...categories.entries()]
        .map(([category, total]) => ({ category, total }))
        .sort((a, b) => b.total - a.total);
}

export function getClientHealthScore(business) {
    const overdueCount = business.invoices.filter((invoice) => normalizeInvoiceStatus(invoice) === "overdue").length;
    const missingExpenseInfo = business.expenses.filter((expense) => {
        return !expense.supplierId || !expense.category || (expense.deductible && !expense.receiptName);
    }).length;
    const months = recentMonthKeys(2);
    const monthlyRevenue = getMonthlyRevenue(business, 2);
    const currentRevenue = monthlyRevenue.find((item) => item.key === months[1])?.total || 0;
    const previousRevenue = monthlyRevenue.find((item) => item.key === months[0])?.total || 0;
    const trendPenalty = currentRevenue < previousRevenue ? 15 : 0;
    const score = Math.max(
        0,
        100 - Math.min(32, overdueCount * 8) - Math.min(25, missingExpenseInfo * 5) - trendPenalty
    );

    return {
        score,
        overdueCount,
        missingExpenseInfo,
        trend: currentRevenue >= previousRevenue ? "Stable or improving" : "Revenue dropped"
    };
}

export function buildReport(business, type) {
    const metrics = getDashboardMetrics(business);
    if (type === "sales") {
        return {
            title: "Sales Report",
            headers: ["Invoice", "Client", "Date", "Status", "Total"],
            rows: business.invoices.map((invoice) => [
                invoice.number,
                getClientName(business, invoice.clientId),
                invoice.issueDate,
                normalizeInvoiceStatus(invoice),
                formatMoney(invoiceTotals(invoice).total)
            ])
        };
    }

    if (type === "expenses") {
        return {
            title: "Expense Report",
            headers: ["Date", "Supplier", "Category", "Amount", "Deductible"],
            rows: business.expenses.map((expense) => [
                expense.date,
                getSupplierName(business, expense.supplierId),
                expense.category,
                formatMoney(expense.amount),
                expense.deductible ? "Yes" : "No"
            ])
        };
    }

    if (type === "tax") {
        return {
            title: "Tax/VAT Summary",
            headers: ["Metric", "Amount"],
            rows: [
                ["Output VAT on invoices", formatMoney(metrics.outputTax)],
                ["Input VAT on deductible expenses", formatMoney(metrics.inputTax)],
                ["Estimated VAT payable", formatMoney(metrics.taxEstimate)]
            ]
        };
    }

    if (type === "cashflow") {
        const months = recentMonthKeys(6);
        return {
            title: "Cash Flow Report",
            headers: ["Month", "Income", "Expenses", "Net Cash Flow"],
            rows: months.map((month) => {
                const income = business.invoices
                    .filter((invoice) => normalizeInvoiceStatus(invoice) === "paid")
                    .filter((invoice) => monthKey(invoice.paidAt || invoice.issueDate) === month)
                    .reduce((total, invoice) => total + invoiceTotals(invoice).total, 0);
                const expenses = business.expenses
                    .filter((expense) => monthKey(expense.date) === month)
                    .reduce((total, expense) => total + parseAmount(expense.amount), 0);
                return [monthLabel(month), formatMoney(income), formatMoney(expenses), formatMoney(income - expenses)];
            })
        };
    }

    return {
        title: "Profit & Loss Report",
        headers: ["Metric", "Amount"],
        rows: [
            ["Income", formatMoney(metrics.totalIncome)],
            ["Expenses", formatMoney(metrics.totalExpenses)],
            ["Net Profit", formatMoney(metrics.netProfit)]
        ]
    };
}
