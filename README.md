# Parallax Morning Brief

**A Python market-intelligence pipeline that turns financial newsletters and cross-asset market data into a concise, human-reviewed morning brief.**

Parallax Morning Brief is a project by **Parallax Research Group** — *the view depends on where you stand.*

[Visit Parallax Research Group](https://parallaxresearchgroup.ca) · [View the sample newsletter](sample_preview.html)

> **Every market has multiple angles.**

Parallax reads selected market newsletters alongside equity, FX, and U.S. Treasury data. It identifies distinct developments, groups overlapping coverage, ranks what matters, writes a cohesive morning brief, checks the finished edition, and sends personalized HTML emails to confirmed subscribers.

The core design choice is simple: **story selection happens before writing**. Python decides which developments enter the editorial package; the language model then writes from that bounded set of stories and market observations.

---

## How It Works

```text
Financial newsletters                 Market data
         │                                │
         └──────────────┬─────────────────┘
                        ▼
                 Parse and filter
                        │
                        ▼
               Extract market stories
                        │
                        ▼
                Group related stories
                        │
                        ▼
                  Score and rank
                        │
                        ▼
              Select 2–3 developments
                        │
                        ▼
                   AI writer
                        │
                        ▼
                   AI editor
                        │
                        ▼
                  Quality checks
                        │
                 ┌──────┴──────┐
                 │             │
               Fail           Pass
                 │             │
                Stop           ▼
                         HTML newsletter
                               │
                               ▼
                        Active subscribers
                           via Supabase
                               │
                               ▼
                             Resend
                               │
                               ▼
                       Subscriber inboxes
```

> **Select first. Write second. Send only after validation.**

---

## What the Pipeline Does

A run can:

1. Retrieve current equity, FX, and U.S. Treasury market data;
2. Read newly received newsletters from a dedicated Gmail label;
3. Remove promotional, administrative, and irrelevant email content;
4. Extract individual market developments;
5. Group newsletters that cover the same underlying story;
6. Rank story groups using consistent editorial signals;
7. Select a small set of distinct developments;
8. Generate a complete morning brief with Gemini;
9. Run a second editorial pass over the full edition;
10. Validate the result against publication rules;
11. Render the final newsletter as HTML;
12. Retrieve confirmed subscribers from Supabase;
13. Add an individual unsubscribe link for each recipient;
14. Deliver the newsletter through Resend; and
15. Record what has already been covered so old material is not treated as new on the next successful run.

If there is not enough meaningful material, Parallax does not force an edition. If the finished brief fails its quality checks, it is not sent.

---

## What Readers Receive

### Market Read

A short explanation of the overall market picture rather than a repetition of the price tables.

### Market Snapshot

The current version tracks:

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

The newsletter presents them as:

```text
Equities      Last       Chg %
FX            Spot       Chg %
UST Yields    Yield      Chg bp
```

FX changes are shown neutrally because a higher currency pair is not inherently positive or negative.

### The Parallax

A short section that connects two pieces of market evidence that may initially look unrelated or contradictory.

### Worth Knowing

Usually two or three of the day's most relevant developments, with an explanation of what happened and why it matters.

### What's Moving

Upcoming events and catalysts when the source material provides enough support to include them.

### The Open Question

A plain-English markets-interview question designed to help readers practice explaining financial concepts.

Example:

> **Why can higher bond yields make stocks less attractive?**

The aim is not trivia. It is to explain the mechanism clearly and identify what a market participant would watch next.

---

## How Stories Are Selected

Multiple newsletters often cover the same event. Parallax groups that overlapping coverage before ranking it so repeated reporting does not dominate the edition.

The ranking considers:

| Factor | What it measures |
|---|---|
| Coverage | How much editorial attention the development received |
| Market move | Whether related assets moved meaningfully |
| Cross-asset relevance | Whether the story helps explain more than one market |
| Freshness | Whether the development is genuinely new or updated |
| Forward relevance | Whether there is a supported event or catalyst to watch next |
| Reader usefulness | Whether the implications can be explained clearly |
| Source diversity | Whether different publications add useful perspectives |
| Specialist insight | Whether a valuable specialist story deserves inclusion even with limited coverage |

Coverage across several publications is treated as a sign of **attention**, not proof that a claim was independently confirmed.

The ranking layer also limits duplicate themes and rejects obvious promotional or administrative content.

---

## Why Separate Ranking From Writing?

A simpler system could be:

```text
Inbox
  ↓
AI
  ↓
Summary
```

Parallax instead uses:

```text
Newsletters + market data
          ↓
   Extract stories
          ↓
   Group duplicates
          ↓
    Score stories
          ↓
   Select stories
          ↓
       AI writer
          ↓
       AI editor
          ↓
    Quality checks
          ↓
       Newsletter
```

This makes it possible to inspect **why a story was selected** separately from how the model explained it.

The writer does not receive an unstructured inbox and decide what matters on its own. It receives the selected stories and market observations produced by the ranking stage.

---

## Newsletter Sources

Parallax currently reads a mix of broad-market and specialist newsletters delivered to a dedicated Gmail label.

### General market coverage

- **[Reuters Morning Bid][reuters-morning-bid]** — U.S. and global markets, macro, rates, FX, commodities, geopolitics, and major near-term catalysts.
- **[Axios Markets][axios-markets]** — concise market and economic analysis across major financial themes.
- **[Yahoo Finance Morning Brief][yahoo-morning-brief]** — weekday coverage of the major narratives, headlines, and events shaping markets and the economy.

### Specialist and thematic coverage

- **[Apollo — The Daily Spark][apollo-daily-spark]** — daily data-driven analysis of the U.S. economy, inflation, and capital markets from Apollo Chief Economist Torsten Slok.
- **[Off The Charts by Andrew Sarna][off-the-charts]** — chart-driven commentary across macro, equities, rates, commodities, and market positioning.
- **[Orange Juice Newsletter by FXStreet][orange-juice]** — market commentary with a strong FX and macro focus.

To enter the pipeline, a newsletter must be delivered to the source Gmail account and carry the label:

```text
PRG-Market-Newsletters
```

Known-source metadata helps Parallax distinguish broad-market coverage from specialist analysis. It does **not** make one publication automatically more reliable than another.

Source material is used internally to identify, group, rank, and explain market developments. Parallax does not republish complete newsletters, articles, charts, images, or long excerpts. Original content remains the property of the respective publishers and authors.

Inclusion does not imply affiliation with, sponsorship of, or endorsement by those publications.

---

## Market Data

Market observations are currently retrieved using the [`yfinance`][yfinance] Python package, which accesses Yahoo Finance market data.

The pipeline handles:

- latest available prices and yields;
- daily percentage moves;
- Treasury yield changes in basis points;
- FX quote conventions; and
- different trading-session dates across asset classes.

Market data may be delayed and is not intended to replace institutional market-data services.

---

## AI's Role

Gemini is used for writing and editing — not for controlling the entire pipeline.

```text
Selected stories
      +
Market data
      │
      ▼
   AI writer
      │
      ▼
   AI editor
      │
      ▼
Python checks
```

The first AI call writes the complete edition from the selected material. The second reviews the edition as a whole. Python then decides whether the result satisfies the publication requirements.

If the ranking stage cannot find enough distinct material, the writing stage is skipped entirely.

---

## Quality Controls

A generated newsletter is not automatically publishable.

Before delivery, the pipeline checks areas including:

- whether enough distinct stories were selected;
- whether the ranking stage passed;
- whether required sections are present;
- whether the stories match the material selected earlier;
- whether source names are allowed;
- whether upcoming events are supported by the source material;
- whether the title is usable;
- whether the Open Question follows its required format; and
- whether the final editorial pass succeeded.

If these checks fail, the edition is not sent and successful-run state is not advanced.

```text
Edition
   │
   ▼
Quality checks
   │
 ┌─┴─┐
 │   │
Fail Pass
 │   │
Stop Send
```

---

## Preventing Repeated Stories

Parallax keeps lightweight state between runs.

It records:

- Gmail messages already processed;
- the time of the previous successful edition; and
- recently covered stories.

After a successful edition, previously used newsletters are not treated as fresh inputs on the next run.

Recent-story memory also helps reduce repetitive coverage across consecutive editions.

---

## Subscriber System

Subscriber state is stored in Supabase.

The basic lifecycle is:

```text
Website signup
      │
      ▼
   pending
      │
      │ email confirmation
      ▼
    active
      │
      │ unsubscribe
      ▼
 unsubscribed
```

Only confirmed subscribers with:

```text
status = active
```

are eligible to receive an edition.

The public Parallax Research Group website manages signup, confirmation, and unsubscribe interactions. The website and this newsletter pipeline are maintained as separate repositories.

---

## Email Delivery

Final newsletters are delivered through Resend using the Parallax Research Group domain.

Each subscriber receives an individual email rather than being placed on a shared recipient list. This allows Parallax to:

- keep subscriber addresses private;
- provide individual unsubscribe links;
- handle delivery failures separately; and
- preserve the newsletter's HTML design.

A configurable recipient limit also acts as a fail-safe against unexpectedly large broadcasts.

---

## Failure Handling

The pipeline is designed to stop rather than manufacture an edition when something important goes wrong.

### Not enough stories

```text
Insufficient material
        ↓
Skip AI writing
        ↓
Do not send
```

### Failed quality checks

```text
Newsletter generated
        ↓
Checks fail
        ↓
Do not send
        ↓
State unchanged
```

### Delivery failure

Source and story state advances only after at least one subscriber delivery is accepted.

If some recipients succeed and others fail, successful recipients are not deliberately sent the same edition again just because another delivery failed.

---

## Ranking Audits

Parallax saves a local JSON record of the ranking process for each run.

These records make it possible to inspect:

- candidate stories;
- grouped stories;
- scores;
- score components;
- selected developments; and
- ranking quality.

Private newsletter evidence is removed from the redacted audit representation.

Generated audit files remain outside the public Git repository.

---

## Tech Stack

| Area | Technology |
|---|---|
| Core pipeline | Python |
| Newsletter ingestion | Gmail API |
| Market data | yfinance / Yahoo Finance |
| AI writing and editing | Gemini API |
| Subscriber database | Supabase / PostgreSQL |
| Email delivery | Resend |
| Testing | Python `unittest` |
| Version control | Git / GitHub |

---

## Repository Structure

```text
Parallax-Morning-Brief/
│
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
│   ├── subscriber_store.py
│   ├── broadcast_sender.py
│   └── utils.py
│
├── tests/
├── SUPABASE_SCHEMA.sql
├── sample_preview.html
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

Generated and private files such as:

```text
.venv/
outputs/
debug/
state/
credentials.json
token.json
```

are excluded from version control.

---

## Running Locally

### 1. Clone

```powershell
git clone https://github.com/NirmayT/Parallax-Morning-Brief.git
cd Parallax-Morning-Brief
```

### 2. Create a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for the current session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

### 4. Run the tests

```powershell
py -m compileall src tests
py -m unittest discover -s tests -v
```

Run deterministic tests before using external API quota.

---

## Configuration

Secrets are supplied through environment variables and must not be committed to Git.

The application uses variables including:

```text
GEMINI_API_KEY

SUPABASE_URL
SUPABASE_SECRET_KEY

RESEND_API_KEY
RESEND_FROM_EMAIL
RESEND_REPLY_TO

PUBLIC_SITE_URL
BROADCAST_MAX_RECIPIENTS

PUBLISHER_NAME
COMPLIANCE_CONTACT_EMAIL
SUBSCRIPTION_DISCLOSURE
```

Gmail authorization additionally uses local:

```text
credentials.json
token.json
```

Both must remain private.

See `.env.example` for sanitized configuration examples.

---

## Gmail Setup

Create a Google Cloud OAuth client for a desktop application and place the downloaded configuration in:

```text
credentials.json
```

The first authorization creates:

```text
token.json
```

Create the Gmail label:

```text
PRG-Market-Newsletters
```

and apply it to newsletters that should enter the pipeline.

Gmail is used for source ingestion. Subscriber newsletters are delivered separately through Resend.

---

## Running the Pipeline

### Dry Run

```powershell
py src/main.py --dry-run --force
```

A dry run can retrieve market data, read new newsletters, rank stories, generate an edition when sufficient material exists, validate it, and save the resulting HTML locally.

It does not broadcast the newsletter or advance successful-run state.

If there is not enough material, the program exits before the AI writing stage.

### Live Run

```powershell
py src/main.py --force
```

For a publishable edition:

```text
Generate
   ↓
Validate
   ↓
Save HTML
   ↓
Load active subscribers
   ↓
Add unsubscribe links
   ↓
Send through Resend
   ↓
Update successful-run state
```

If the edition fails validation, live delivery is blocked.

---

## Development Workflow

The recommended sequence is:

```text
1. Compile the project
2. Run deterministic tests
3. Review code changes
4. Run a dry run
5. Inspect the generated newsletter
6. Inspect the ranking audit
7. Confirm the edition passed
8. Test delivery in a controlled inbox
9. Run production delivery
```

Useful commands:

```powershell
py -m compileall src tests
py -m unittest discover -s tests -v
py src/main.py --dry-run --force
```

---

## Security

Before a public push:

```powershell
git status
git diff
git diff --cached
```

A useful staged-secret scan is:

```powershell
git grep --cached -n -I -E "AIza|sb_secret_|service_role|re_[A-Za-z0-9_]+"
```

Never commit:

- API keys;
- `.env`;
- `credentials.json`;
- `token.json`;
- Supabase secret keys;
- Resend API keys;
- subscriber emails or exports;
- raw newsletter bodies;
- generated outputs;
- ranking evidence containing private source text; or
- local state.

If a credential is exposed, rotate it rather than merely deleting it from the latest version of the repository.

---

## Design Decisions

### Why not let the AI choose all the stories?

Because deciding **what matters** and deciding **how to explain it** are different problems.

Separating them makes story selection easier to inspect and test.

### Why group stories before ranking?

Several newsletters may cover the same event. Without grouping, a widely repeated story could occupy several slots in one edition.

### Why keep single-source specialist stories?

A useful market development can matter even when only one specialist publication covers it.

### Why remember previous stories?

A morning brief should emphasize what changed rather than repeatedly summarizing yesterday's narrative.

### Why send individual emails?

Individual delivery protects subscriber privacy and makes personalized unsubscribe links possible.

### Why allow the system to publish nothing?

Because a weak story should not be invented simply to make the newsletter look complete.

---

## Known Limitations

- Yahoo Finance data may be delayed and is not institutional-grade.
- Email parsing depends on how each publisher structures its newsletter.
- Image-heavy newsletters may provide limited usable text.
- External API limits or outages can interrupt a run.
- Ranking weights reflect editorial judgment rather than an objective definition of importance.
- Several publications covering the same story does not necessarily mean they independently verified it.
- The system uses supplied newsletter evidence but does not independently fact-check every underlying claim.
- Email clients can render the same HTML differently.
- Human review remains part of the publication process.

---

## Future Work

Potential extensions include:

- scheduled production runs;
- richer delivery records;
- automated bounce and complaint handling;
- expanded market-data sources;
- additional specialist research inputs;
- historical evaluation of story rankings; and
- additional automated editorial tests.

The goal is to add complexity only when an observed failure or new requirement justifies it.

---

## Parallax Research Group

**Parallax** is the apparent shift in an object's position when viewed from different vantage points. The object itself does not change; the angle does.

That idea motivates Parallax Research Group: independent, data-driven work on markets and technology that tries to examine more than one perspective rather than defaulting to the loudest narrative.

Parallax Morning Brief is one project built around that principle.

[Visit Parallax Research Group](https://parallaxresearchgroup.ca)

---

## Disclaimer

Parallax Morning Brief is a personal research and portfolio project.

It is not investment advice, a trading system, an institutional market-data service, or a guarantee of the accuracy of third-party source material.

Source publications and their underlying content remain the property of their respective publishers and authors. Inclusion does not imply affiliation, sponsorship, or endorsement.

Market data may be delayed.

---

## License

See [`LICENSE`](LICENSE).

---

## Source References

The newsletter-source descriptions above are based on the publishers' own pages:

[reuters-morning-bid]: https://www.reuters.com/podcasts/reuters-morning-bid-trailer-2025-11-21/
[axios-markets]: https://pages.axios.com/axios-newsletters-2-0
[yahoo-morning-brief]: https://finance.yahoo.com/topic/morning-brief/
[apollo-daily-spark]: https://www.apollo.com/wealth/insights-news/insights/daily-spark
[off-the-charts]: https://offthecharts.substack.com/
[orange-juice]: https://www.fxstreet.com/
[yfinance]: https://github.com/ranaroussi/yfinance
