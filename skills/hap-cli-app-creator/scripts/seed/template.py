"""Build a deterministic *fill template* from an app's captured controls.

Store-native adaptation of the hap-cli-app-creator skill's
``generate_fill_templates.py``. Differences from that script:

* the store keeps the server's **integer** control ``type`` (not the
  PascalCase CODE), so we map it via ``control_type_codes.type_id_to_code``;
* options are stored as ``{key, value}`` objects;
* only a **whitelist** of value-bearing CODEs is emitted — every other
  type (AutoNumber / Formula / Rollup / Lookup / Barcode / Divider /
  Section / Signature / Embed / Button …) is a layout/computed/read-only
  field and gets no value;
* the server-generated *reverse* half of a two-way relation is dropped
  (seeding either half syncs both); it is detected by a bidirectional
  control whose ``sourceControlId`` is a dangling placeholder — NOT by
  ``enumDefault`` (that is the cardinality 1=single/2=multi, not the
  direction, and mis-fires on many-to-many relations).

The template is what an AI reads (together with INSTRUCTIONS.md) to author
the ``_seed_data.json`` data file.
"""
from __future__ import annotations

from typing import Any

from scripts._hapmeta.control_type_codes import type_id_to_code

# Whitelist of value-bearing field CODEs — only these get sample data.
# Everything else is layout / computed / read-only and is never written.
FILLABLE_CODES: set[str] = {
    "Text", "PhoneNumber", "LandlinePhone", "Email", "Number", "Certificate",
    "Currency", "SingleSelect", "MultipleSelect", "Dropdown", "Attachment",
    "Date", "DateTime", "Region", "Collaborator", "Department", "Rating",
    "Relation", "SubTable", "CascadingSelect", "Checkbox", "Location",
    "RichText", "Time", "OrgRole",
}

# Option-bearing CODEs whose validOptions we surface.
_OPTION_CODES = {"SingleSelect", "MultipleSelect", "Dropdown"}

# System columns every worksheet carries — never user-written.
_SYSTEM_FIELD_IDS = {"rowid", "ownerid", "caid", "ctime", "utime", "uaid"}


def _code_of(control: dict[str, Any]) -> str | None:
    """Map a control's integer ``type`` to its CODE, or None if unknown."""
    t = control.get("type")
    if not isinstance(t, int):
        return None
    try:
        return type_id_to_code(t)
    except ValueError:
        return None


def _is_reverse_relation(
    control: dict[str, Any], all_control_ids: set[str]
) -> bool:
    """A two-way relation has an authored *forward* half and a server-
    generated *reverse* half — skip the reverse (seeding either side syncs
    both; writing both would be redundant/conflicting).

    The two halves are NOT distinguished by ``enumDefault``: that is the
    *cardinality* (1 = single / 2 = multi), not the direction. Using it as
    the discriminator mis-fires on many-to-many relations, where the
    forward half is also multi (enumDefault==2) and would be wrongly
    dropped while the reverse is exposed.

    The reliable marker is ``sourceControlId``: the forward half points at
    its real partner control (resolves to a live controlId); the reverse
    half keeps the dangling placeholder the server reserved (resolves to
    nothing). So: bidirectional + unresolvable sourceControlId => reverse.
    """
    if control.get("type") != 29:
        return False
    adv = control.get("advancedSetting") or {}
    if adv.get("bidirectional") != "1":
        return False  # one-way relation — always keep
    src = control.get("sourceControlId")
    return not (src and src in all_control_ids)


def _field_from_control(
    c: dict[str, Any], *, wsid: str, id_to_name: dict[str, str],
    relation_deps: set[str], all_control_ids: set[str],
) -> dict[str, Any] | None:
    """Map one control to a fillable-field dict, or None if it should be
    skipped (system / read-only / non-whitelisted / reverse relation).

    For SubTable, recurse into ``relationControls`` to expose ``childFields``.
    Relation targets are accumulated into ``relation_deps`` (logical names).
    """
    cid = c.get("controlId") or c.get("id") or ""
    if cid in _SYSTEM_FIELD_IDS:
        return None
    if str(c.get("alias", "")).startswith("_"):
        return None
    code = _code_of(c)
    if code is None or code not in FILLABLE_CODES:
        return None
    if _is_reverse_relation(c, all_control_ids):
        return None

    field: dict[str, Any] = {
        "name": c.get("controlName") or c.get("name") or "", "type": code,
    }
    if code in _OPTION_CODES:
        field["validOptions"] = [
            o.get("value") for o in (c.get("options") or [])
            if not o.get("isDeleted") and o.get("value")
        ]
    if code == "Relation":
        ds = c.get("dataSource") or ""
        target_name = id_to_name.get(ds, ds)
        field["dataSource"] = target_name
        # enumDefault is the cardinality: 1 = single, 2 = multi. Surface it
        # so the author writes the right number of @refs (a single relation
        # takes ONE; a multi relation takes a list).
        field["multi"] = c.get("enumDefault") == 2
        if ds == wsid:
            field["isSelfRelation"] = True
        elif target_name:
            relation_deps.add(target_name)
    if code == "SubTable":
        children: list[dict[str, Any]] = []
        for cc in c.get("relationControls") or []:
            cf = _field_from_control(
                cc, wsid=wsid, id_to_name=id_to_name, relation_deps=relation_deps,
                all_control_ids=all_control_ids)
            if cf is not None:
                children.append(cf)
        field["childFields"] = children
    return field


def build_fill_template(store) -> list[dict[str, Any]]:
    """Return one template dict per worksheet:

        {worksheetId, worksheetName, fieldCount, fillableFields[], relationDeps[]}

    where each fillableField is
        {name, type(CODE), isTitle?, validOptions?, dataSource?(logical),
         multi?(for Relation), isSelfRelation?, childFields?(for SubTable)}.
    """
    ws_index = store.index("worksheet")
    id_to_name: dict[str, str] = {
        wid: name for name, wid in ws_index.get("byName", {}).items()
    }

    # All real controlIds across every worksheet — used to tell an authored
    # forward relation (sourceControlId resolves here) from a server-
    # generated reverse half (sourceControlId is a dangling placeholder).
    all_control_ids: set[str] = set()
    for item in store.list("worksheet"):
        for c in store.worksheet_controls(item["id"]):
            cid = c.get("controlId") or c.get("id")
            if cid:
                all_control_ids.add(cid)

    templates: list[dict[str, Any]] = []
    for item in store.list("worksheet"):
        wsid = item["id"]
        fillable: list[dict[str, Any]] = []
        relation_deps: set[str] = set()
        title_marked = False
        first_text: dict[str, Any] | None = None

        for c in store.worksheet_controls(wsid):
            field = _field_from_control(
                c, wsid=wsid, id_to_name=id_to_name, relation_deps=relation_deps,
                all_control_ids=all_control_ids)
            if field is None:
                continue
            # Title field: server flags it via attribute==1; else fall back
            # to the first Text field on the (top-level) worksheet.
            if c.get("attribute") == 1:
                field["isTitle"] = True
                title_marked = True
            elif field["type"] == "Text" and first_text is None:
                first_text = field
            fillable.append(field)

        if not title_marked and first_text is not None:
            first_text["isTitle"] = True

        templates.append({
            "worksheetId": wsid,
            "worksheetName": item["name"],
            "fieldCount": len(fillable),
            "fillableFields": fillable,
            "relationDeps": sorted(relation_deps),
        })

    return templates
