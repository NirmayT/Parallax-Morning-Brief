# Parallax Morning Brief

> **Every market has multiple angles.**

Parallax Morning Brief is a human-reviewed Python market-intelligence pipeline that turns selected market newsletters and cross-asset market data into a concise, Substack-ready morning brief.

The system deliberately separates **selection from writing**. Python and bounded AI tasks extract, cluster, score, and select market developments first. A full-edition writer then receives only the ranked editorial package and observed market data, followed by a holistic editor and deterministic quality gate.

Parallax is a **personal research and portfolio project**. It is not a trading system, investment adviser, institutional market-data product, or automatic fact-checker.

---

## What the brief contains

A successful edition is designed to include:

- A distinctive editorial title built around a tension, idea, or contrast rather than a simple market recap
- Date and risk mood
- A one-sentence opening
- One emphasized key line
- A concise **Market Read** that interprets the cross-asset picture without repeating the tables
- A market snapshot for equities, FX, and U.S. Treasury yields
- **The Parallax**, a three-sentence connection between different pieces of evidence
- **Worth Knowing**, normally 2–3 distinct developments with concise explanations
- **What's Moving** only when supported catalysts add something new
- **The Open Question**, a plain-English markets-interview question with a three-sentence teaching answer

The pipeline is intentionally allowed to omit weak material instead of filling space.

---

## Why Parallax is different

A simple inbox summarizer asks a language model to decide what sounds important. Parallax makes the editorial process explicit and auditable.

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
Local preview / Gmail delivery
            |
            v
Human review and Substack publish
```

The governing principle is:

> **Select first. Write second. Publish manually.**

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

The ranking layer also applies editorial constraints such as limiting duplicate themes, rejecting obvious promotional or administrative content, and preferring genuinely distinct developments.

---


## Newsletter sources & attribution

Parallax currently ingests selected market and economic newsletters delivered to the dedicated Gmail label. The production source set should reflect the newsletters actually being used rather than an aspirational source list.

Current editorial inputs:

- **Axios Markets** — market trends and economic analysis from Axios. Official newsletter directory: https://pages.axios.com/axios-newsletters-2-0
- **Yahoo Finance Morning Brief** — Yahoo Finance's weekday markets newsletter. Official Morning Brief page: https://finance.yahoo.com/topic/morning-brief/
- **Apollo — The Daily Spark** — daily data-driven macro and capital-markets analysis from Apollo Chief Economist Torsten Slok. Official page: https://www.apollo.com/wealth/insights-news/insights/daily-spark

These publications and their underlying content remain the property of their respective publishers and authors. Parallax does **not** redistribute complete newsletters, paid articles, charts, images, or long source excerpts. Newsletter material is used internally for story extraction, clustering, ranking, grounding, and attribution; the reader-facing brief provides concise original synthesis and identifies contributing publications.

Inclusion of a publication does not imply affiliation with, sponsorship of, or endorsement of Parallax. Cross-publication coverage is treated as an editorial attention signal rather than proof of independent factual confirmation.

### Market-data source

Newsletter evidence and numerical market data serve different roles in the system. Parallax currently retrieves its prototype market observations through the `yfinance` Python library, which accesses Yahoo Finance market data. This data may be delayed and should not be treated as institutional-grade pricing.

When additional newsletters are added to the production Gmail label, this section should be updated to reflect the actual source set.

## Market conventions

The current snapshot tracks:

### Equities
- S&P 500
- Nasdaq 100
- S&P/TSX Composite

### FX
- EUR/USD
- USD/CNY
- USD/CAD
- USD/JPY

### U.S. Treasury yields
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

Treasury values returned by Yahoo are already percentage yields. For example, a value of `4.696` is displayed as `4.70%`. A change from `4.653` to `4.696` is approximately `+4 bp`.

Different asset groups may reflect different sessions. The brief displays each group's latest available observation.

---

## Project structure

This repository currently uses a **flat module layout inside `src/`**. There is no `src/parallax/` package directory yet, and that is intentional for v1.0.

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
│   └── utils.py
├── tests/
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
└── sample_preview.html
```

Generated or private directories such as `.venv/`, `debug/`, `outputs/`, and `state/` are intentionally excluded from Git.

---

# Installation

The commands below assume **Windows PowerShell** and Python 3.11+.

## 1. Clone the repository

```powershell
git clone https://github.com/YOUR-USERNAME/Parallax-Morning-Brief.git
cd Parallax-Morning-Brief
```

If you are working from a local copy rather than GitHub, open the project root in VS Code.

## 2. Create a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then reopen the terminal and activate the environment again.

## 3. Upgrade pip

```powershell
py -m pip install --upgrade pip
```

## 4. Install dependencies

```powershell
py -m pip install -r requirements.txt
```

---

# Configuration

## Gemini API key

Parallax reads the Gemini API key from the environment variable:

```text
GEMINI_API_KEY
```

For the current PowerShell session:

```powershell
$env:GEMINI_API_KEY="your-key-here"
```

To store it for your Windows user account:

```powershell
setx GEMINI_API_KEY "your-key-here"
```

Open a new terminal after using `setx`.

Do **not** commit the real key to the repository.

---

## Gmail OAuth

Create a Google Cloud OAuth client for a **Desktop application** and download the client configuration.

Save the file in the project root as:

```text
credentials.json
```

Parallax requires Gmail read and send access:

```text
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
```

On the first authenticated run, Google will open an authorization flow and create:

```text
token.json
```

Both `credentials.json` and `token.json` are ignored by Git and must remain private.

If you change OAuth scopes after a token has already been created, delete `token.json` locally and authorize again.

---

## Gmail newsletter label

Create this exact Gmail label:

```text
PRG-Market-Newsletters
```

Apply it to the newsletters you want Parallax to consider.

The pipeline is designed to tolerate irrelevant labeled mail, but your source set should still consist primarily of genuine market/economic newsletters.

---

## Delivery configuration

Set your sender and private Substack publish-by-email address in your local `src/config.py` configuration.

For example:

```python
SENDER_EMAIL = "your-gmail@gmail.com"
RECIPIENT_EMAIL = "your-private-substack-address"
```

Treat the Substack publish-by-email address as a secret.

For a public repository, replace personal values with placeholders before committing.

---

# Running Parallax

Because the entry point lives in `src/`, run commands from the project root.

## Compile the code

```powershell
py -m compileall src tests
```

## Run the deterministic regression suite

```powershell
py -m unittest discover -s tests -v
```

All deterministic tests should pass before spending any AI quota.

## Dry run

```powershell
py src/main.py --dry-run --force
```

A dry run:

- retrieves current market data
- reads eligible Gmail newsletters
- extracts and ranks stories
- generates the edition
- validates the output
- saves a local HTML preview
- does **not** update processed-message state

Inspect:

```text
outputs/brief_*.html
debug/ranking_*.json
```

## Live delivery

Only after a successful dry run and manual review:

```powershell
py src/main.py --force
```

A live run should update processed IDs, story memory, and the last-run timestamp **only after delivery succeeds**.

Final publication on Substack should remain manual.

---

# What a healthy run looks like

A healthy run should resemble:

```text
[RANK] Extracted ... story candidates; fallback share ...%.
[RANK] Grouped candidates into ... story clusters.
[RANK] Ranked ... clusters; selected 2 or 3.
[RANK] Audit saved: debug\ranking_....json
[SYNTH] Cohesive full draft and holistic editor pass completed.
[PIPELINE] Dry run: state not updated. Publish ready: True.
```

The exact number of selected stories can vary. Two strong stories are preferable to padding the edition with a weak third.

---

# Quality gate

A generated edition is not considered publishable merely because it looks complete.

The quality gate checks structural and editorial requirements including:

- required sections
- approved source names
- selected cluster identity
- supported watch items
- sentence-count contracts where required
- usable title structure
- plain-English Open Question format
- successful ranking quality
- successful synthesis quality

If the gate fails:

- live delivery is blocked
- state is not updated
- a local internal-review preview is retained for debugging

This behavior is intentional.

---

# Editorial principles

Parallax aims to avoid the common failure mode where every section repeats the same market move.

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

The system prefers omission over filler.

---

# The Open Question

The Open Question is designed as a lightweight daily interview-preparation exercise.

A good question should:

- use plain English
- be one sentence
- connect to the day's edition
- teach a reusable market concept
- be answerable without calculations
- avoid trivia and unexplained jargon
- sound plausible in a markets or finance interview

The answer uses three sentences:

1. direct answer
2. mechanism
3. what a market participant would watch

Example:

> **Why can higher bond yields make stocks less attractive?**

The goal is not to test obscure knowledge. It is to help readers practice explaining markets clearly.

---

# Substack workflow

Parallax intentionally keeps the final publication decision manual.

Recommended workflow:

```text
1. Run deterministic tests
2. Run a dry run
3. Review HTML
4. Review ranking audit
5. Confirm Publish ready: True
6. Run one live delivery
7. Inspect the actual Substack draft
8. Publish manually
```

Do not rely only on browser preview. Email-to-Substack rendering can differ from the local HTML.

---

# GitHub release checklist

Before the first public push:

```powershell
git init
git add .
git status
git diff --cached
```

Inspect every staged file.

Confirm that none of the following are staged:

- `.env`
- `credentials.json`
- `token.json`
- Gemini API keys
- private Substack publishing address
- `outputs/`
- `debug/`
- `state/`
- `.venv/`
- raw newsletter bodies
- private ranking evidence
- employer/internal email or research
- personal subscriber information

Then commit:

```powershell
git commit -m "Release Parallax v1.0"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/Parallax-Morning-Brief.git
git push -u origin main
```

After the public repository has been verified:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

---

# Privacy and responsible use

Use only personal accounts and public or personally subscribed material.

Do not commit or publish:

- employer research
- internal communications
- client information
- non-public commentary
- full paid-newsletter content
- raw email payloads
- credentials or tokens

Parallax uses newsletter evidence internally for extraction and grounding. The public repository should contain code, tests, documentation, and sanitized examples only.

---

# Known limitations

- Yahoo Finance data may be delayed and is not institutional-grade market data.
- Newsletter extraction quality depends on email structure.
- Image-heavy newsletters may contribute little usable text.
- Free AI quotas and rate limits can interrupt synthesis.
- Ranking weights are editorial heuristics, not objective measures of importance.
- Cross-publication coverage does not imply independent confirmation.
- The system grounds writing in supplied evidence but does not independently fact-check the underlying newsletters.
- Final publication still requires human review.

---

# Suggested calibration after launch

Once the system is stable, publish several real editions before changing the ranking model.

Track:

```text
Algorithmic lead vs. your preferred lead
Selected stories vs. your preferred shortlist
Duplicate clusters
Missed merges
Weak stories admitted
Useful stories omitted
Fallback usage
Unsupported or repetitive language
Open Question quality
```

Change ranking or clustering logic only after a repeated real-world failure appears.

---

# Portfolio framing

A concise description:

> Built an end-to-end Python market-intelligence pipeline integrating Gmail ingestion, cross-asset market data, structured story extraction, deterministic clustering, transparent editorial ranking, cohesive AI synthesis, quality gates, and human-reviewed Substack delivery.

The repository demonstrates the engineering system. The publication demonstrates the editorial output.

---

# Disclaimer

Personal project. Not affiliated with or endorsed by any employer.

Market data may be delayed. Parallax does not provide investment advice, trading recommendations, or guaranteed factual verification of third-party newsletter claims.
