# Nightshift Evidence Dashboard

A static Next.js replay dashboard for property-based test generation, detective refutation triage, and spend accounting.

Built for the **Nightshift** autonomous defect detection project.

---

## Architecture & Security
- **Zero Server Dependencies:** Built with Next.js App Router configured for static export (`output: "export"`). Bundles all verified datasets into standalone HTML, CSS, and JS.
- **Airgapped & Secret-Free:** No API keys, credentials, or private repository URLs are included in the frontend bundle.
- **Strict Data Scrubbing:** Every run report is sanitized via `scripts/sync-run.ts` prior to inclusion, stripping local filesystem paths, authorization headers, and private IPs.

---

## Getting Started

### Prerequisites
- Node.js >= 20.0.0
- npm >= 10.0.0

### Local Development
```bash
cd dashboard
npm install
npm run dev --webpack -p 3000
```
Open [http://localhost:3000](http://localhost:3000) to view the live dashboard.

### Validation & Build
```bash
# 1. Validate all datasets against Schema v1 and scan for secret leaks
npm run validate-data

# 2. Check TypeScript types
npm run typecheck

# 3. Compile static export
npm run build
```
Static production files are emitted to `dashboard/out/`.

---

## Deploying to Vercel (Production)

1. **Import Repository**: In your Vercel Dashboard, import the `nightshift` GitHub repository.
2. **Project Settings**:
   - **Framework Preset**: Next.js
   - **Root Directory**: `dashboard`
   - **Build Command**: `npm run build`
   - **Output Directory**: `out` (or default Next.js export)
3. **Environment Variables**: None required.
4. **Deployment Protection**: Ensure the project is public so judges can access the URL without requiring a Vercel team invite.

---

## Ingesting New Real-Package Runs

When a new campaign finishes on a team machine:
```bash
npx tsx scripts/sync-run.ts <path-to-run-folder>
```
This validates the report against Schema v1, redacts sensitive paths/tokens, copies the artifacts into `data/runs/<run_id>/`, and updates `data/runs/index.json`.
