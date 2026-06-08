"""Vendored, stdlib-only copies of the two hap_cli helpers the build
pipeline needs to construct field-control wire payloads locally.

The published skill must NOT depend on the ``hap_cli`` Python package being
importable — it may only shell out to the ``hap`` binary and run its own
bundled files. These modules are byte-faithful copies of
``hap_cli/core/control_type_codes.py`` and
``hap_cli/core/worksheet_templates.py`` with their one cross-module import
made relative. Keep them in sync if the upstream wire format changes.
"""
