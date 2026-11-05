import { formatMoney, getClientName, invoiceTotals } from "./calculations.js";

function triggerDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

export function downloadCsv(report) {
    const rows = [report.headers, ...report.rows];
    const csv = rows
        .map((row) => row.map((cell) => `"${String(cell ?? "").replaceAll('"', '""')}"`).join(","))
        .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const filename = `${report.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.csv`;
    triggerDownload(blob, filename);
}

function pdfSafe(value) {
    return String(value ?? "")
        .replace(/[^\x20-\x7e]/g, "?")
        .replace(/\\/g, "\\\\")
        .replace(/\(/g, "\\(")
        .replace(/\)/g, "\\)");
}

function buildSimplePdf(lines) {
    const content = lines
        .slice(0, 42)
        .map((line, index) => `BT /F1 ${index < 2 ? 15 : 10} Tf 48 ${790 - index * 18} Td (${pdfSafe(line)}) Tj ET`)
        .join("\n");
    const objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        `<< /Length ${content.length} >>\nstream\n${content}\nendstream`
    ];
    let pdf = "%PDF-1.4\n";
    const offsets = [0];
    objects.forEach((object, index) => {
        offsets.push(pdf.length);
        pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
    });
    const xrefOffset = pdf.length;
    pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
    offsets.slice(1).forEach((offset) => {
        pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
    });
    pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;
    return pdf;
}

export function downloadInvoicePdf(invoice, business) {
    const clientName = getClientName(business, invoice.clientId);
    const totals = invoiceTotals(invoice);
    const lines = [
        `${business.name}`,
        `Invoice ${invoice.number}`,
        `Client: ${clientName}`,
        `Issue Date: ${invoice.issueDate}`,
        `Due Date: ${invoice.dueDate}`,
        `Status: ${invoice.status}`,
        "",
        "Items"
    ];

    for (const item of invoice.items || []) {
        const quantity = Number(item.quantity || 0);
        const price = Number(item.price || 0);
        lines.push(`${item.description || "Item"} | Qty ${quantity} | ${formatMoney(price)} | VAT ${item.taxRate || 0}%`);
    }

    lines.push("");
    lines.push(`Subtotal: ${formatMoney(totals.subtotal)}`);
    lines.push(`VAT/Tax: ${formatMoney(totals.tax)}`);
    lines.push(`Total: ${formatMoney(totals.total)}`);
    if (invoice.notes) lines.push(`Notes: ${invoice.notes}`);

    const blob = new Blob([buildSimplePdf(lines)], { type: "application/pdf" });
    triggerDownload(blob, `${invoice.number || "invoice"}.pdf`);
}
