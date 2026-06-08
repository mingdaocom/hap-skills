"""Worksheet field-type CODE ↔ ControlTypeId mapping.

The HAP server uses an integer ``type`` (a.k.a. ControlTypeId) for
every worksheet column. Two surface naming schemes layer on top:

* The hap-app-builder skill (and the upstream MCP server) uses a set of
  PascalCase ``CODE`` names — ``Text``, ``Number``, ``Relation``,
  ``SubTable``, etc. This is the user-facing vocabulary.
* The existing ``hap_cli.core.worksheet_templates`` module uses
  SCREAMING_SNAKE_CASE names — ``TEXT``, ``NUMBER``, ``RELATE_SHEET``,
  ``SUB_LIST``, etc. — for the template builder.

This module is the single source of truth for builder ``CODE`` ↔
ControlTypeId, plus the bridge to the existing templates module.

Region is one logical CODE that maps to *three* ControlTypeIds
distinguished by precision level (province=19, city=23, county=24).
Callers using the CODE ``Region`` MUST supply ``regionLevel`` ("province"
| "city" | "county") to disambiguate on the write side; on the read
side ``region_level_from_type_id`` recovers the level for inclusion in
the normalized output.
"""
from __future__ import annotations

from typing import Optional


# Single canonical CODE ↔ ControlTypeId map. Order matches the table in
# the hap-app-builder skill so a side-by-side diff is trivial. Region is
# the only one-to-many entry (three ids collapse to one CODE).
CODE_TO_TYPE_ID: dict[str, int] = {
    "Text": 2,
    "PhoneNumber": 3,
    "LandlinePhone": 4,
    "Email": 5,
    "Number": 6,
    "Certificate": 7,
    "Currency": 8,
    "SingleSelect": 9,
    "MultipleSelect": 10,
    "Dropdown": 11,
    "Attachment": 14,
    "Date": 15,
    "DateTime": 16,
    # Region: three precision levels share one CODE. Default to county
    # (the most common UI choice) when caller omits regionLevel.
    "Region": 24,
    "DynamicLink": 21,
    "Divider": 22,
    "AmountInWords": 25,
    "Collaborator": 26,
    "Department": 27,
    "Rating": 28,
    "Relation": 29,
    "Lookup": 30,
    "Formula": 31,
    "Concatenate": 32,
    "AutoNumber": 33,
    "SubTable": 34,
    "CascadingSelect": 35,
    "Checkbox": 36,
    "Rollup": 37,
    "DateFormula": 38,
    "CodeScan": 39,
    "Location": 40,
    "RichText": 41,
    "Signature": 42,
    "OCR": 43,
    "Role": 44,
    "Embed": 45,
    "Time": 46,
    "Barcode": 47,
    "OrgRole": 48,
    "Button": 49,
    "APIQuery": 50,
    "QueryRecord": 51,
    "Section": 52,
    "FunctionFormula": 53,
    "CustomField": 54,
}

# Reverse: every ControlTypeId we know about → CODE. Region's three
# precision-level ids all map back to "Region".
TYPE_ID_TO_CODE: dict[int, str] = {v: k for k, v in CODE_TO_TYPE_ID.items()}
TYPE_ID_TO_CODE[19] = "Region"
TYPE_ID_TO_CODE[23] = "Region"


# Bridge to hap_cli.core.worksheet_templates SCREAMING_SNAKE names.
# Keep this colocated so a new field type only needs three edits: this
# file (CODE→typeId, template name), the templates module (defaults),
# and the type-id reverse map auto-derives.
CODE_TO_TEMPLATE_NAME: dict[str, str] = {
    "Text": "TEXT",
    "PhoneNumber": "MOBILE_PHONE",
    "LandlinePhone": "TELEPHONE",
    "Email": "EMAIL",
    "Number": "NUMBER",
    "Certificate": "CRED",
    "Currency": "MONEY",
    "SingleSelect": "FLAT_MENU",
    "MultipleSelect": "MULTI_SELECT",
    "Dropdown": "DROP_DOWN",
    "Attachment": "ATTACHMENT",
    "Date": "DATE",
    "DateTime": "DATE_TIME",
    # Region levels handled in code_to_template_name() with the
    # regionLevel hint; defaults to AREA_COUNTY when unspecified.
    "Region": "AREA_COUNTY",
    "DynamicLink": "RELATION",
    "Divider": "SPLIT_LINE",
    "AmountInWords": "MONEY_CN",
    "Collaborator": "USER_PICKER",
    "Department": "DEPARTMENT",
    "Rating": "SCORE",
    "Relation": "RELATE_SHEET",
    "Lookup": "SHEET_FIELD",
    "Formula": "FORMULA_NUMBER",
    "Concatenate": "CONCATENATE",
    "AutoNumber": "AUTO_ID",
    "SubTable": "SUB_LIST",
    "CascadingSelect": "CASCADER",
    "Checkbox": "SWITCH",
    "Rollup": "SUBTOTAL",
    "DateFormula": "FORMULA_DATE",
    # CodeScan (39) and Role (44) have no template entry yet — callers
    # using these must pass raw control dicts via --controls until the
    # template module learns them.
    "Location": "LOCATION",
    "RichText": "RICH_TEXT",
    "Signature": "SIGNATURE",
    "OCR": "OCR",
    "Embed": "EMBED",
    "Time": "TIME",
    "Barcode": "BAR_CODE",
    "OrgRole": "ORG_ROLE",
    "Button": "SEARCH_BTN",
    "APIQuery": "SEARCH",
    "QueryRecord": "RELATION_SEARCH",
    "Section": "SECTION",
    "FunctionFormula": "FORMULA_FUNC",
    "CustomField": "CUSTOM",
}


_REGION_LEVEL_TO_TYPE_ID = {
    "province": 19,
    "city": 23,
    "county": 24,
}
_REGION_TYPE_ID_TO_LEVEL = {v: k for k, v in _REGION_LEVEL_TO_TYPE_ID.items()}
_REGION_LEVEL_TO_TEMPLATE_NAME = {
    "province": "AREA_PROVINCE",
    "city": "AREA_CITY",
    "county": "AREA_COUNTY",
}


def code_to_type_id(code: str, region_level: Optional[str] = None) -> int:
    """Look up the wire ControlTypeId for a builder CODE.

    ``region_level`` ("province"/"city"/"county") refines Region to the
    right one of 19/23/24. Ignored for non-Region codes. Defaults to
    county when omitted on a Region call.
    """
    if code == "Region":
        return _REGION_LEVEL_TO_TYPE_ID.get(region_level or "county", 24)
    if code not in CODE_TO_TYPE_ID:
        raise ValueError(
            f"Unknown field type CODE {code!r}. "
            f"Valid codes: {sorted(CODE_TO_TYPE_ID)}"
        )
    return CODE_TO_TYPE_ID[code]


def type_id_to_code(type_id: int) -> str:
    """Look up the builder CODE for a wire ControlTypeId.

    Region's 19/23/24 all collapse to "Region"; callers needing the
    precision level should call ``region_level_from_type_id``.
    Unknown ids raise ValueError so we surface unmapped server types
    instead of silently dropping them.
    """
    if type_id not in TYPE_ID_TO_CODE:
        raise ValueError(
            f"Unknown ControlTypeId {type_id}. Known ids: {sorted(TYPE_ID_TO_CODE)}"
        )
    return TYPE_ID_TO_CODE[type_id]


def region_level_from_type_id(type_id: int) -> Optional[str]:
    """Return "province"/"city"/"county" for region ids, else None."""
    return _REGION_TYPE_ID_TO_LEVEL.get(type_id)


def code_to_template_name(code: str, region_level: Optional[str] = None) -> str:
    """Bridge a builder CODE to the SCREAMING_SNAKE name understood by
    ``hap_cli.core.worksheet_templates.build_control``.

    ``region_level`` refines Region; see ``code_to_type_id``.
    """
    if code == "Region":
        return _REGION_LEVEL_TO_TEMPLATE_NAME.get(region_level or "county", "AREA_COUNTY")
    if code not in CODE_TO_TEMPLATE_NAME:
        raise ValueError(
            f"No template binding for CODE {code!r}. "
            f"Either add it to CODE_TO_TEMPLATE_NAME or pass raw control "
            f"dicts via --controls."
        )
    return CODE_TO_TEMPLATE_NAME[code]
