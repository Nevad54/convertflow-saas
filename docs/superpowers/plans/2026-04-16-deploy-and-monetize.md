# ConvertFlow Deployment And Monetization Plan

Last updated: 2026-04-16
Status: Ready to execute
Owner: Codex

## Goal

Launch ConvertFlow in a way that can generate revenue quickly, while reducing the risk of spending weeks on infrastructure before validating demand.

This plan treats deployment and monetization as two tracks:

- Track A: fast revenue through a manual or semi-manual service offer
- Track B: deployable SaaS foundation for recurring subscription revenue

## Why This Plan

The product already has meaningful capability:

- 30 document and PDF tools are present
- local-first workflows are implemented
- edit-PDF redesign and QA are complete

But the hosted product is not yet monetization-ready because:

- Linux deployment blockers still exist for Office to PDF
- Docker deployment files are not complete
- auth, quotas, and billing are not implemented
- pricing and landing-page positioning are still broad

## Recommended Strategy

Do not wait for the full SaaS to be finished before trying to earn money.

Execute in this order:

1. Sell one narrow outcome manually
2. Remove deployment blockers
3. Deploy a hosted beta
4. Add simple limits and billing
5. Expand from one wedge into broader subscriptions

## Best Initial Paid Wedge

Start with one use case instead of marketing all 30 tools equally.

Recommended first wedge:

- scanned invoice, contract, and form recovery into editable outputs

Strong backup wedges:

- Office to PDF with better fidelity than lightweight web tools
- review/finalize workflows: edit, redact, sign, watermark, protect

## Phase 0: Revenue Before SaaS

Goal: collect money before full productization.

### Offer

Sell ConvertFlow as a service:

- "We recover messy PDFs and scans into editable business files"
- "We clean, convert, redact, and finalize documents fast"

### Delivery model

- user submits a job by email, form, or direct message
- files are processed using the current local app
- output is delivered manually
- payment is collected per job or via simple payment link

### Suggested pricing

- one-off simple conversion: $9 to $19
- messy scan recovery: $29 to $79
- business batch work: custom quote

### Success metric

Get the first 3 paid customers before investing heavily in subscription plumbing.

## Phase 1: Deployment Blockers

Goal: make the app Linux-hostable.

### Required work

- implement LibreOffice fallback for Word, PowerPoint, and Excel to PDF
- remove or isolate Windows-only dependency issues such as `pywin32`
- add Docker support for the app
- run Ollama as a sidecar container

### Existing references

- `SAAS_PLAN.md`
- `docs/superpowers/plans/2026-04-16-libreoffice-fallback.md`
- `docs/superpowers/plans/2026-04-16-ollama-docker-sidecar.md`

### Exit criteria

- app builds in Docker
- app starts on Linux
- Office to PDF works without Windows COM
- Ollama integration is env-driven and works in containerized setup

## Phase 2: Hosted Beta

Goal: put a public version online fast.

### Recommended host

Use Railway first for speed.

Reasons:

- faster than self-managing a VPS
- easy env-var setup
- easy service split for app plus Ollama
- lower ops overhead during early validation

### Scope

Deploy only a stable subset publicly at first:

- merge
- split
- compress
- PDF to Word
- Word to PDF
- image to document
- edit/redact/sign

Keep unstable or expensive flows behind a beta flag if needed.

### Exit criteria

- public URL works
- core conversions succeed
- logs are visible
- temporary file handling is safe enough for beta use

## Phase 3: Simple Monetization Layer

Goal: charge for usage with the smallest possible system.

### Build only what is needed

- email/password auth
- free tier with daily cap
- paid tier with Stripe Checkout
- plan flag stored per user

### Suggested v1 pricing

- Free: 3 conversions/day
- Pro: $12/month

### Important simplification

Do not build complex teams, credits, or enterprise billing yet.
Keep one subscription tier until real usage shows where limits should move.

### Exit criteria

- users can sign up
- users can pay
- users are upgraded automatically after webhook confirmation
- free users hit a clear limit and see an upgrade prompt

## Phase 4: Landing Page That Sells One Outcome

Goal: improve conversion instead of just listing tools.

### Messaging direction

Lead with one outcome:

- "Turn messy scans and PDFs into editable business documents"

Support with proof:

- fast
- local-first roots
- broad format support
- business-ready finalize tools

### Page sections

- hero with one strong value proposition
- before/after style examples
- use cases for invoices, contracts, forms, and internal ops
- pricing
- FAQ about privacy and file handling

### Avoid

- leading with "30 tools" as the main promise
- making AI the entire identity
- presenting every feature at equal weight

## Phase 5: Demand And Distribution

Goal: get real traffic instead of waiting for organic luck.

### Best early channels

- direct outreach to operations-heavy small businesses
- founder-led demos to admin, legal, finance, and real-estate users
- SEO pages for specific intent terms
- short demo videos showing messy-document recovery

### Example SEO targets

- scan to editable Word
- invoice PDF to Excel
- redact and sign PDF online
- contract PDF to Word

### Success metric

Get 20 users who complete a real workflow, then optimize pricing and onboarding from those sessions.

## Risks

### Technical risks

- Linux conversion fidelity may differ from Windows COM output
- AI-assisted flows may be slow or expensive at scale
- file retention and temp-storage rules must be clarified before public launch

### Business risks

- broad positioning may weaken conversion
- users may value one wedge far more than the full suite
- subscription work can consume time before demand is proven

## Execution Order

1. Finish Linux and Docker blockers
2. Deploy hosted beta
3. Launch manual paid service in parallel
4. Add auth and Stripe
5. Rework landing page around one wedge
6. Measure which workflow actually converts

## Immediate Next Actions

1. Execute LibreOffice fallback plan
2. Create `docker-compose.yml` and `Dockerfile`
3. remove `pywin32` from Linux deployment path
4. deploy beta to Railway
5. create a simple pricing and intake page

## Definition Of Success

This plan is working if, within the next cycle, ConvertFlow is:

- deployable on Linux
- reachable at a public URL
- able to collect at least one payment
- positioned around one outcome people will actually pay for
