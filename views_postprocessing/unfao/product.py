"""The declared FAO delivery product (ADR-013 §4.2a's "views-postprocessing
configuration" — settled home per the 2026-07-19 CCP decision recorded in the ADR).

Everything here is a **declaration**, never an inference: the delivery refuses to
ship until reality matches these constants, and changing the product is a human
decision plus an edit here — reviewed, git-historied, fail-loud. One reason to
change: the FAO partner relationship.

The constants and their contract homes:

- ``TARGETS`` — the expected target set (§4.2a): a run is *complete* only when every
  target listed here has a manifested Hop-A leg. Adding a target follows Amendment
  A1 (§7a): maintainer names it, producer's mapping gains an entry, this tuple
  gains an entry. Wire vocabulary only — never internal model names.
- ``S_MIN`` — the §6 no-collapse floor passed to ``delivery.draws``. 2 is the
  walking-skeleton value; the production pinning mechanism is an OPEN maintainer
  item (ADR-013 Post-adoption record, 2026-07-19).
- ``CONSUMER_DOCUMENT_NAME`` — the §4.1a store-document ``name`` pin. faoapi's
  query layer filters on it unconditionally; a document under any other name is
  invisible to the consumer. Config-owned by views-faoapi; changing it is a
  contract amendment.
- ``UPLOAD_ENABLED`` — the §11.4 upload interlock: ``False`` means the sink writes
  artifacts locally and never calls the store. Overriding requires an explicit
  launch-config declaration (wired in the sink story), and the first live
  enablement is gated on faoapi's C-161 closure notice.
"""

from __future__ import annotations

TARGETS: tuple[str, ...] = ("lr_ged_sb", "lr_ged_ns", "lr_ged_os")

S_MIN: int = 2

CONSUMER_DOCUMENT_NAME: str = "un_fao"

UPLOAD_ENABLED: bool = False
