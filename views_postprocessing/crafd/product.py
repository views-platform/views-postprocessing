"""The declared CRAF'd delivery product (ADR-013 §4.2a's "views-postprocessing
configuration"). Clone of ``unfao/product.py`` for the second external partner —
the Complex Risk Analytics Fund (CRAF'd), served by views-crafdapi.

Everything here is a **declaration**, never an inference: the delivery refuses to
ship until reality matches these constants, and changing the product is a human
decision plus an edit here — reviewed, git-historied, fail-loud. One reason to
change: the CRAF'd partner relationship.

CRAF'd is FAO *extended* (same VIEWS forecasts, same PRIO-GRID geography, same
cadence): for now the same three conflict-fatality series, delivered to CRAF'd's
own bucket. The uncertainty *surface* CRAF'd adds — exceedance probabilities
alongside HDI/MAP — lives in the consumer (views-crafdapi ADR-034), not here; the
producer ships the same posterior-sample wire the FAO producer ships. Additional
targets, when CRAF'd names them, are an Amendment A1 edit to ``TARGETS`` below.

The constants and their contract homes:

- ``TARGETS`` — the expected target set (§4.2a): a run is *complete* only when every
  target listed here has a manifested Hop-A leg. Adding a target follows Amendment
  A1 (§7a): maintainer names it, producer's mapping gains an entry, this tuple
  gains an entry. Wire vocabulary only — never internal model names.
- ``S_MIN`` — the §6 no-collapse floor passed to ``delivery.draws``.
- ``CONSUMER_DOCUMENT_NAME`` — the §4.1a store-document ``name`` pin. views-crafdapi's
  query layer filters on it unconditionally; a document under any other name is
  invisible to the consumer. Config-owned by views-crafdapi (ADR-034 §6); changing
  it is a contract amendment.
- ``UPLOAD_ENABLED`` — the §11.4 upload interlock: ``False`` means the sink writes
  artifacts locally and never calls the store. Overriding requires an explicit
  launch-config declaration. The consumer-side precondition this once named — the
  views-crafdapi selection guard in production — was **met 2026-08-12**
  (views-crafdapi#53).
  What gates it now is **ours**: the upload path has never run against a real store —
  þing-02 D2 forbids testing against production and the org holds no other project
  (#18). That decision is **views-appwrite#171**.
"""

from __future__ import annotations

TARGETS: tuple[str, ...] = ("lr_ged_sb", "lr_ged_ns", "lr_ged_os")

S_MIN: int = 2

CONSUMER_DOCUMENT_NAME: str = "un_crafd"

UPLOAD_ENABLED: bool = False
