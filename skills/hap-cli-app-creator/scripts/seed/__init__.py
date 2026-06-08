"""Test-data seeding for an already-built HAP app.

Three-stage workflow (see scripts/seed/INSTRUCTIONS.md):

  1. (mechanical) ``build_fill_template`` reads the app's captured control
     metadata and emits a per-table list of *fillable* fields — only the
     whitelist of value-bearing types, with validOptions / dataSource /
     isTitle / isSelfRelation / relationDeps. Forward fields only
     (reverse relations are dropped).
  2. (AI) following INSTRUCTIONS.md, author a declarative data file
     ``{worksheetName: [rows]}`` where each row may carry a ``_ref``
     logical label and relation fields reference rows via ``@label``.
  3. (mechanical) ``seed_app`` topologically orders the tables by
     relation dependency, pushes each via ``hap record batch-create``,
     captures the real rowIds and substitutes them into downstream
     ``@label`` references. Self-relations are seeded in two phases.
"""
from scripts.seed.template import build_fill_template
from scripts.seed.executor import seed_app

__all__ = ["build_fill_template", "seed_app"]
