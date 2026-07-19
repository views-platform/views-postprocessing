"""ADR-013 Hop-B wire mechanics (epic #105).

One closure: this package changes when the wire contract
(``docs/ADRs/013_sampled_forecast_wire_contract.md``) changes, and for no other
reason. The FAO *product* declaration lives outside it (``unfao/product.py`` —
different reason to change); representation-free *rules* live below it
(``delivery/``); the manager above composes it.
"""
