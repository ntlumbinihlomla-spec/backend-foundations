# Financial CSV Dashboard Offer

## Positioning

I build simple financial dashboards for SMEs that turn messy CSV exports or CSV source links into clean summaries, batch analytics, and client-ready reports.

## Core Offer

Upload CSVs or connect a CSV source URL, then get clean summaries and batch analytics.

The product is intentionally narrow:

1. Upload one or more CSV files, or connect a CSV source URL such as a published CSV export.
2. Choose the numeric column that matters.
3. Review totals, averages, ranges, and contribution bars.
4. Export a client-ready HTML report that can be printed or saved as PDF.

## Pricing

Free Demo:

- Sample CSV uploads
- CSV source URL import
- Single-file summaries
- Batch analytics preview
- Client report preview

Monthly Access:

- Suggested starting price: R299 per month
- Stripe Checkout subscription
- Paid API key provisioning
- Upload library, batch analytics, and client report export
- CSV source connector for repeatable imports

Custom Dashboard:

- Quoted per client
- Branded dashboard
- Custom report fields
- Deployment and handover

## Demo Flow

1. Open `frontend/freelance.html` for the client-facing service page.
2. Open `frontend/landing.html` for the product demo page.
3. Click `Open Free Demo`.
4. Save the demo API key or use a paid key after checkout.
5. Upload a CSV or connect a CSV source URL with a numeric column such as `amount`.
6. Refresh the library and select one or more files.
7. Run `Batch Summary`.
8. Click `Export Client Report`.

## Deployment Checklist

Set these environment variables on Render:

- `API_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_PRICE_ID`
- `STRIPE_WEBHOOK_SECRET`
- `PUBLIC_BASE_URL`

Stripe setup:

1. Create a recurring monthly Price.
2. Set `STRIPE_PRICE_ID` to that Price ID.
3. Add a webhook endpoint: `https://your-api.onrender.com/billing/webhook`.
4. Subscribe to `checkout.session.completed` and `customer.subscription.deleted`.
5. Set `PUBLIC_BASE_URL` to the deployed API base URL.

## Outreach Copy

Subject: Quick financial CSV dashboard for your team

Hi,

I build simple financial dashboards for SMEs that turn CSV exports or CSV source links into clean summaries, batch analytics, and client-ready reports.

If your team still reviews financial CSVs manually, I can set up a small hosted dashboard where you upload files or connect a CSV source link, choose the column that matters, and export a report for review or client sharing.

I can show you a working demo this week.
