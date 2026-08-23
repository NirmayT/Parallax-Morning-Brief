# Parallax Morning Brief

**An auditable Python market-intelligence pipeline that turns selected newsletters and cross-asset data into a concise, human-reviewed morning brief.**

Parallax Morning Brief is part of **Parallax Research Group** — *the view depends on where you stand.* The broader project publishes independent, data-driven work on markets and technology. [Read more and join the newsletter](https://parallax-research-plum.vercel.app/).

> **Every market has multiple angles.**

Parallax deliberately separates **selection from writing**. The pipeline first extracts, clusters, scores, and selects developments; only then does the language model write the edition from the bounded editorial package and observed market data. A deterministic quality gate decides whether an edition is eligible for delivery.

The project is a personal research and portfolio project. It is not a trading system, investment adviser, institutional market-data product, or automatic fact-checker.

---

## Current status

The editorial pipeline is functional and covered by deterministic regression tests. The project is now migrating from a single-recipient/Substack-oriented delivery workflow to **first-party subscriber delivery**:

```text
Parallax website
      |
      v
double-opt-in signup
      |
      v
Supabase subscriber database
      |
      v
active subscribers
      |
      +-------------------------------+
                                      |
Gmail newsletters + market data       |
              |                       |
              v                       |
        extract / rank                |
              |                       |
              v                       |
       synthesize / edit              |
              |                       |
              v                       |
      deterministic gate              |
              |                       |
              v                       |
        exact HTML edition            |
              |                       |
              +-----------------------+
              |
              v
        Resend delivery
              |
              v
      subscriber inboxes
```

**Important:** the website integration and public subscriber broadcast are still being completed. Until that work is verified end-to-end, use dry runs and controlled self-tests rather than broadcasting to a real list.

---

## What the brief contains

A successful edition is designed to include:

- a distinctive editorial title built around a tension, idea, or contrast rather than a market recap;
- date and risk mood;
- a one-sentence opening;
- one emphasized key line;
- a concise **Market Read** that interprets the cross-asset picture without repeating the tables;
- a market snapshot for equities, FX, and U.S. Treasury yields;
- **The Parallax**, a short connection between different pieces of evidence;
- **Worth Knowing**, normally 2–3 distinct developments with actual explanation rather than headline restatement;
- **What's Moving** only when supported catalysts add something new; and
- **The Open Question**, a plain-English markets-interview question with a short teaching answer.

The pipeline is intentionally allowed to omit weak material instead of filling space.

---

## Why Parallax is different

A simple inbox summarizer asks a model to decide what sounds important. Parallax makes the editorial process explicit and auditable.

```text
Gmail newsletters + market data
            |
            v
Parse and filter
            |
            v
Labeled-text story extraction
            |
            v
Deterministic similarity clustering
            |
            v
Transparent cluster scoring
            |
            v
Editorial selection
            |
            v
Full-edition AI writer
            |
            v
Holistic AI editor
            |
            v
Python validation + quality gate
            |
            v
Exact HTML artifact
            |
            v
Human review / controlled delivery
```

The governing principle is:

> **Select first. Write second. Deliver only after validation.**

---

## Ranking model

Story clusters are scored using transparent editorial factors:

| Factor | Purpose |
|---|---|
| Cross-publication coverage | Measures broad editorial attention |
| Related market move | Connects stories to observed market movement |
| Cross-asset relevance | Rewards developments that matter across asset classes |
| Freshness | Rewards new or materially updated developments |
| Forward relevance | Rewards supported near-term catalysts |
| Reader usefulness | Favors developments with explainable market implications |
| Source diversity | Rewards a mix of general and specialist perspectives |
| Specialist protection | Prevents useful one-source specialist work from disappearing automatically |

Cross-publication coverage is an **attention signal**, not independent factual confirmation. Multiple publications may rely on the same upstream reporting.

The ranking layer also limits duplicate themes, rejects obvious promotional/administrative material, and prefers genuinely distinct developments.

---

## Newsletter sources and attribution

Parallax currently ingests selected market and economic newsletters delivered to a dedicated Gmail label.

Current editorial inputs include:

- **Axios Markets** — market trends and economic analysis from Axios. <https://pages.axios.com/axios-newsletters-2-0>
- **Yahoo Finance Morning Brief** — Yahoo Finance's weekday markets newsletter. <https://finance.yahoo.com/topic/morning-brief/>
- **Apollo — The Daily Spark** — data-driven macro and capital-markets analysis from Apollo Chief Economist Torsten Slok. <https://www.apollo.com/wealth/insights-news/insights/daily-spark>

These publications and their underlying content remain the property of their respective publishers and authors. Parallax does **not** redistribute complete newsletters, paid articles, charts, images, or long source excerpts. Source material is used internally for extraction, clustering, ranking, grounding, and attribution; the reader-facing brief provides concise original synthesis and identifies contributing publications.

Inclusion does not imply affiliation with, sponsorship of, or endorsement of Parallax.

### Market data

Parallax currently retrieves prototype market observations through the [`yfinance`](https://github.com/ranaroussi/yfinance) Python library, which accesses Yahoo Finance market data. Data may be delayed and should not be treated as institutional-grade pricing.

When the production Gmail source set changes, this section should be updated to match the sources actually used.

---

## Market conventions

The current snapshot tracks:

**Equities**
- S&P 500
- Nasdaq 100
- S&P/TSX Composite

**FX**
- EUR/USD
- USD/CNY
- USD/CAD
- USD/JPY

**U.S. Treasury yields**
- US 3M
- US 5Y
- US 10Y
- US 30Y

The rendered table uses:

```text
Equities     Last     Chg %
FX           Spot     Chg %
UST Yields   Yield    Chg bp
```

FX changes are displayed neutrally because a rising currency pair is not inherently good or bad.

Treasury values returned by Yahoo are already percentage yields. For example, `4.696` is displayed as `4.70%`; a move from `4.653` to `4.696` is approximately `+4 bp`.

Different asset groups may reflect different sessions. The brief displays each group's latest available observation.

---

## Repository structure

The current project uses a flat Python module layout inside `src/`.

```text
Parallax-Morning-Brief/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── market_data.py
│   ├── gmail_client.py
│   ├── email_parser.py
│   ├── newsletter_filter.py
│   ├── story_ranker.py
│   ├── synthesis.py
│   ├── story_memory.py
│   ├── brief_builder.py
│   ├── brief_sections.py
│   ├── email_sender.py
│   ├── subscriber_store.py      # first-party subscriber lookup
│   ├── broadcast_sender.py      # exact-HTML Resend delivery
│   └── utils.py
├── tests/
│   └── ...
├── SUPABASE_SCHEMA.sql
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
└── sample_preview.html
```

Generated/private directories such as `.venv/`, `debug/`, `outputs/`, and `state/` should remain excluded from Git.

The public website is maintained in a **separate repository**. It owns the signup/confirmation/unsubscribe UX; this repository owns newsletter generation and broadcast delivery.

---

# Installation

The examples below assume **Windows PowerShell** and Python 3.11+.

## 1. Clone

```powershell
git clone https://github.com/YOUR-USERNAME/Parallax-Morning-Brief.git
cd Parallax-Morning-Brief
```

## 2. Create and activate a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for the current session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```powershell
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

## 4. Verify the repository before using API quota

```powershell
py -m compileall src tests
py -m unittest discover -s tests -v
```

All deterministic tests should pass before running the live pipeline.

---

# Configuration

Real secrets belong in environment variables or a local ignored `.env` workflow — **never in `.env.example`, source code, commits, issues, screenshots, or documentation**.

A sanitized `.env.example` should document only variable names/placeholders.

## Gemini

Required:

```text
GEMINI_API_KEY
```

Current PowerShell session:

```powershell
$env:GEMINI_API_KEY="your-key-here"
```

Persistent Windows user variable:

```powershell
setx GEMINI_API_KEY "your-key-here"
```

Open a new terminal after `setx`.

---

## Gmail OAuth: source ingestion

Gmail is used to **ingest source newsletters**, not as the long-term subscriber broadcast engine.

Create a Google Cloud OAuth client for a **Desktop application**, download the client configuration, and save it in the project root as:

```text
credentials.json
```

The ingestion workflow requires Gmail read access. If legacy/testing code still sends through Gmail, it may also require send access.

On first authorization, Google creates:

```text
token.json
```

Both files must remain private and ignored by Git.

Create this exact Gmail label:

```text
PRG-Market-Newsletters
```

Apply it to newsletters Parallax should consider.

---

# First-party subscriber delivery

The production direction is:

- **Supabase** — subscriber state;
- **Resend** — exact-HTML email transport;
- **Parallax website** — subscribe/confirm/unsubscribe UX;
- **this Python repo** — generation, validation, subscriber lookup, personalization, and broadcast.

## Supabase

The Python backend expects:

```text
SUPABASE_URL
SUPABASE_SECRET_KEY
```

Use a **server-side Supabase secret key** dedicated to this Python pipeline. Do not reuse a website/frontend credential and never expose a secret key in browser code.

Example:

```powershell
$env:SUPABASE_URL="https://YOUR_PROJECT.supabase.co"
$env:SUPABASE_SECRET_KEY="YOUR_SERVER_SECRET"
```

The `subscribers` table contract is defined in:

```text
SUPABASE_SCHEMA.sql
```

The broadcast path reads only subscribers whose status is:

```text
active
```

A production subscriber lifecycle is expected to be:

```text
pending -> active -> unsubscribed
```

with `bounced` and `complained` available for suppression/delivery handling.

## Resend

The broadcast sender expects:

```text
RESEND_API_KEY
RESEND_FROM_EMAIL
RESEND_REPLY_TO
PUBLIC_SITE_URL
BROADCAST_MAX_RECIPIENTS
```

Example placeholders:

```powershell
$env:RESEND_API_KEY="YOUR_RESEND_KEY"
$env:RESEND_FROM_EMAIL="Parallax Morning Brief <brief@updates.example.com>"
$env:RESEND_REPLY_TO="reply@example.com"
$env:PUBLIC_SITE_URL="https://example.com"
$env:BROADCAST_MAX_RECIPIENTS="90"
```

`PUBLIC_SITE_URL` is used to construct each subscriber's unique unsubscribe URL.

For development, use Resend's permitted test workflow and send only to your own authorized test address. A real public broadcast should use a domain you control and have authenticated with the provider.

## Website contract

The separate website repository is responsible for:

```text
POST /api/subscribe
GET  /api/confirm?token=...
GET  /unsubscribe?token=...
POST /unsubscribe?token=...
```

Expected behavior:

1. normalize and validate the submitted email;
2. create a `pending` subscriber;
3. require confirmation before `active`;
4. preserve unsubscribe state instead of deleting rows; and
5. keep all Supabase secret credentials server-side.

The newsletter pipeline should never infer consent from a raw email address. Only `active` subscribers are eligible for delivery.

---

# Running Parallax

Run commands from the repository root.

## Dry run

```powershell
py src/main.py --dry-run --force
```

A dry run:

- retrieves current market data;
- reads eligible Gmail newsletters;
- extracts, clusters, and ranks stories;
- generates and validates the edition;
- saves the exact HTML artifact locally; and
- does **not** update processed-message state or broadcast to subscribers.

Inspect:

```text
outputs/brief_*.html
debug/ranking_*.json
```

Dry runs consume AI quota. Run deterministic tests first.

## Live run

A live run is:

```powershell
py src/main.py --force
```

**Do not use live mode against a real subscriber list until the Supabase and Resend integrations have passed controlled self-tests.**

When the first-party broadcast integration is enabled, a publishable live run should:

1. generate and validate the edition;
2. save the exact HTML artifact locally;
3. retrieve `active` subscribers from Supabase;
4. insert a subscriber-specific unsubscribe URL;
5. send an individualized copy through Resend; and
6. update editorial/source state only after at least one delivery is accepted.

If the quality gate fails, live broadcast is blocked.

---

# Delivery safety

The broadcast layer is intentionally conservative.

### Individualized sends

Subscribers receive individual messages rather than a visible recipient list. This:

- protects subscriber privacy;
- allows a unique unsubscribe URL per subscriber; and
- prevents accidental exposure through `To`, `CC`, or `BCC`.

### Unsubscribe

The HTML template contains an invisible delivery marker that is replaced at send time with a subscriber-specific unsubscribe link.

The sender also supplies standard unsubscribe headers. The public website must support the corresponding unsubscribe route.

### Broadcast cap

`BROADCAST_MAX_RECIPIENTS` provides a fail-safe against unexpectedly large sends. Keep it comfortably below your provider's current daily/account limits and increase it deliberately as the system matures.

### Logs and PII

Do not log subscriber email addresses, confirmation tokens, unsubscribe tokens, or raw subscriber records into `debug/` or CI output.

---

# What a healthy run looks like

A healthy editorial dry run should resemble:

```text
[RANK] Extracted ... editorial story candidates...
[RANK] Grouped candidates into ... story clusters.
[RANK] Ranked ... clusters; selected 2 or 3.
[RANK] Audit saved: debug\ranking_....json
[SYNTH] ...
[PIPELINE] Dry run: state not updated. Publish ready: True.
```

A production broadcast additionally reports the number of active subscribers and accepted deliveries without printing subscriber addresses.

The exact number of selected stories can vary. Two strong stories are preferable to padding an edition with a weak third.

---

# Quality gate

A generated edition is not publishable merely because it looks complete.

The gate checks requirements including:

- required sections;
- approved source names;
- selected cluster identity;
- supported watch items;
- sentence-count contracts where required;
- usable, non-recap title structure;
- plain-English Open Question format;
- ranking quality; and
- synthesis quality.

If the gate fails:

- live delivery is blocked;
- editorial/source state is not updated; and
- a local internal-review preview is retained for debugging.

---

# Editorial principles

Each section has a different job:

| Section | Editorial job |
|---|---|
| Title | Create curiosity around the central tension |
| Opening | Orient the reader |
| Key Line | State the most important takeaway |
| Market Read | Interpret the cross-asset setup |
| Market Snapshot | Provide exact levels and moves |
| The Parallax | Connect distinct pieces of evidence |
| Worth Knowing | Explain 2–3 separate developments |
| What's Moving | Surface supported catalysts only when useful |
| Open Question | Teach a reusable markets-interview concept |

The system prefers omission over filler and should not repeat the same story simply to fill multiple sections.

---

## The Open Question

The Open Question is a lightweight daily interview-preparation exercise.

A good question should:

- use plain English;
- be one sentence;
- connect to the day's edition;
- teach a reusable market concept;
- be answerable without calculations;
- avoid trivia and unexplained jargon; and
- sound plausible in a markets or finance interview.

The answer uses three sentences:

1. direct answer;
2. mechanism; and
3. what a market participant would watch.

Example:

> **Why can higher bond yields make stocks less attractive?**

The goal is not obscure knowledge. It is to help readers practice explaining markets clearly.

---

# Testing and development workflow

Use this order to avoid wasting API quota:

```text
1. py -m compileall src tests
2. py -m unittest discover -s tests -v
3. inspect git diff / git status
4. run a dry run
5. inspect outputs/brief_*.html
6. inspect debug/ranking_*.json
7. confirm Publish ready: True
8. use controlled delivery tests
9. only then enable a real broadcast
```

For delivery work, test the links independently:

```text
Python -> Supabase -> active subscriber lookup
Python -> Resend -> your own inbox
Website -> Supabase -> pending/active/unsubscribed
```

Only combine them after each link works on its own.

---

# GitHub hygiene

Before every public push:

```powershell
git status
git diff
git diff --cached
```

A useful secret scan before committing:

```powershell
git grep --cached -n -I -E "AIza|sb_secret_|service_role|re_[A-Za-z0-9_]+"
```

Also inspect for real personal/project email addresses where they should not be public.

Never commit:

- `.env`;
- `credentials.json`;
- `token.json`;
- Gemini keys;
- Supabase secret/service-role keys;
- Resend API keys;
- `outputs/`;
- `debug/`;
- `state/`;
- `.venv/`;
- raw newsletter bodies;
- private ranking evidence;
- subscriber emails or subscriber exports; or
- employer/internal/client material.

If a secret is ever committed or pasted into an untrusted/public location, **rotate it**. Removing it from the latest file is not sufficient once it has been exposed.

---

# Privacy and responsible use

Use personal accounts and public or personally subscribed material only.

Parallax uses newsletter evidence internally for extraction and grounding. The public repository should contain code, tests, documentation, and sanitized examples — not raw source emails or subscriber data.

Subscriber data should be collected only for the stated newsletter purpose, stored minimally, protected by server-side credentials, and suppressed promptly when a reader unsubscribes or complains.

---

# Known limitations

- Yahoo Finance data may be delayed and is not institutional-grade.
- Newsletter extraction quality depends on email structure.
- Image-heavy newsletters may contribute little usable text.
- Free AI/API quotas and rate limits can interrupt synthesis or delivery.
- Ranking weights are editorial heuristics, not objective measures of importance.
- Cross-publication coverage does not imply independent confirmation.
- The system grounds writing in supplied evidence but does not independently fact-check the underlying newsletters.
- HTML email clients can render CSS differently from a normal browser.
- First-party subscriber delivery is still being productionized and should remain in controlled testing until the complete opt-in/unsubscribe flow is verified.
- Human review remains part of the publication process.

---

# Roadmap

Near-term production work:

- [x] deterministic editorial regression suite;
- [x] local exact-HTML generation;
- [x] subscriber database schema;
- [x] Python subscriber-store and Resend delivery modules;
- [ ] website double-opt-in integration;
- [ ] verified sending domain;
- [ ] end-to-end subscribe -> confirm -> receive -> unsubscribe test;
- [ ] bounce/complaint webhook handling and suppression;
- [ ] edition/delivery audit records;
- [ ] scheduled production execution after manual validation.

Longer-term work should be driven by observed failures rather than speculative complexity.

---

# License

See [`LICENSE`](LICENSE).

---

# Disclaimer

Personal project. Not affiliated with or endorsed by any employer or source publication.

Market data may be delayed. Parallax does not provide investment advice, trading recommendations, or guaranteed factual verification of third-party newsletter claims.
