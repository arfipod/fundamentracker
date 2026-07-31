# FundamenTracker Product Context

## Product

FundamenTracker is Ángel's private, self-hosted workspace for monitoring listed
companies through fundamental metrics. It is not a public finance portal, a
social network, or a trading terminal. Its job is to help one investor notice
when a company reaches an interesting valuation, review the evidence, and keep a
small research queue organised.

## Primary jobs

1. Review newly triggered signals and decide whether they deserve research.
2. Maintain a watchlist with valuation, quality, growth, leverage, and capital
   allocation alerts.
3. Inspect a current metric, its provenance, and a real historical series when
   one exists.
4. Keep lightweight status, priority, and tags for each company.
5. Run or schedule scans without losing context.

## Product posture

FundamenTracker is an operating tool. Scanability, data provenance, predictable
controls, and fast repeat use matter more than visual spectacle. The interface
should feel like a calm research ledger: precise, useful, and personal rather
than like a generic AI-generated dashboard.

## Core principles

- Put the next decision before secondary metadata.
- Use colour to communicate state, not to decorate containers.
- Never imply precision or history that the data source cannot support.
- Keep every important action available on touch, keyboard, and narrow screens.
- Prefer direct labels such as “Run scan”, “Add alert”, and “Mark reviewed”.
- Use progressive disclosure for scan settings, provenance, charts, SEC facts,
  and generated research notes.
- Preserve user context: changing views, opening a chart, or editing an alert
  should not unexpectedly reset nearby work.

## Information hierarchy

1. Open signals and triggered alert state.
2. Company, metric, target, and current value.
3. Watchlist workflow status and priority.
4. Data source, freshness, confidence, and history.
5. Scheduled scan details and general market context.

## Content language

The product UI uses concise English consistently. Financial abbreviations remain
where they are standard, but controls and empty states use plain language.
Generated analysis is labelled as an assisted research brief rather than being
presented as authoritative advice.

## Non-goals

- Gamification, social proof, marketing sections, or onboarding carousels.
- Decorative market animations, fake live tickers, or attention-grabbing glows.
- A card for every piece of text.
- Automatic trading or personalised financial advice.
