export const STORAGE_KEY = "ledgerLiteAssistant.v1";

export function uid(prefix = "id") {
    return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export function todayIso() {
    return new Date().toISOString().slice(0, 10);
}

export function monthIso(date = new Date()) {
    return date.toISOString().slice(0, 7);
}

export function createBusiness(name = "Demo Trading Co") {
    const businessId = uid("biz");
    const clientId = uid("client");
    const supplierId = uid("supplier");
    const now = new Date().toISOString();
    const currentYear = new Date().getFullYear();

    return {
        id: businessId,
        name,
        owner: "Owner",
        taxRate: 15,
        clients: [
            {
                id: clientId,
                name: "Thabo Mokoena",
                email: "accounts@mokotrading.example",
                phone: "+27 82 000 1000",
                businessName: "Moko Trading",
                taxNumber: "VAT445001",
                address: "12 Market Road, Cape Town",
                createdAt: now,
                updatedAt: now
            }
        ],
        suppliers: [
            {
                id: supplierId,
                name: "OfficeMart",
                email: "billing@officemart.example",
                phone: "+27 11 000 2000",
                businessName: "OfficeMart Supplies",
                taxNumber: "VAT998877",
                address: "44 Supplier Street, Johannesburg",
                createdAt: now,
                updatedAt: now
            }
        ],
        invoices: [
            {
                id: uid("inv"),
                clientId,
                number: "INV-1001",
                issueDate: `${currentYear}-05-03`,
                dueDate: `${currentYear}-05-17`,
                status: "paid",
                label: "approved",
                notes: "Monthly bookkeeping support.",
                comments: "Paid by EFT.",
                items: [
                    { description: "Bookkeeping support", quantity: 1, price: 2800, taxRate: 15 }
                ],
                createdBy: "Hlomla",
                createdAt: now,
                updatedAt: now,
                paidAt: `${currentYear}-05-12`
            },
            {
                id: uid("inv"),
                clientId,
                number: "INV-1002",
                issueDate: `${currentYear}-06-01`,
                dueDate: `${currentYear}-06-15`,
                status: "unpaid",
                label: "review-needed",
                notes: "Dashboard report pilot.",
                comments: "",
                items: [
                    { description: "CSV dashboard pilot", quantity: 1, price: 2800, taxRate: 15 }
                ],
                createdBy: "Hlomla",
                createdAt: now,
                updatedAt: now
            }
        ],
        expenses: [
            {
                id: uid("exp"),
                date: `${currentYear}-06-02`,
                supplierId,
                category: "Software",
                amount: 399,
                taxRate: 15,
                paymentMethod: "Card",
                notes: "Monthly software tools.",
                comments: "Receipt needed for file.",
                deductible: true,
                receiptName: "",
                label: "missing-info",
                createdBy: "Hlomla",
                createdAt: now,
                updatedAt: now
            },
            {
                id: uid("exp"),
                date: `${currentYear}-05-20`,
                supplierId,
                category: "Office",
                amount: 620,
                taxRate: 15,
                paymentMethod: "EFT",
                notes: "Stationery and printing.",
                comments: "",
                deductible: true,
                receiptName: "office-supplies.pdf",
                label: "approved",
                createdBy: "Hlomla",
                createdAt: now,
                updatedAt: now
            }
        ],
        auditLog: [
            {
                id: uid("audit"),
                action: "seeded",
                entity: "business",
                details: "Demo business created",
                user: "System",
                timestamp: now
            }
        ],
        createdAt: now,
        updatedAt: now
    };
}

export function createDefaultState() {
    const business = createBusiness();
    return {
        version: 1,
        activeBusinessId: business.id,
        currentUser: "Hlomla",
        theme: "light",
        businesses: [business]
    };
}

export function loadState() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (!stored) return createDefaultState();
        const parsed = JSON.parse(stored);
        if (!parsed.businesses?.length) return createDefaultState();
        return parsed;
    } catch {
        return createDefaultState();
    }
}

export function saveState(state) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function getActiveBusiness(state) {
    return state.businesses.find((business) => business.id === state.activeBusinessId) || state.businesses[0];
}

export function addAuditEntry(state, businessId, action, entity, details) {
    const business = state.businesses.find((item) => item.id === businessId);
    if (!business) return;
    business.auditLog.unshift({
        id: uid("audit"),
        action,
        entity,
        details,
        user: state.currentUser || "Unknown",
        timestamp: new Date().toISOString()
    });
    business.updatedAt = new Date().toISOString();
}
