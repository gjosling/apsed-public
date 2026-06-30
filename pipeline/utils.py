"""
Shared constants and utilities used across pipeline scripts.
"""
import re
from pathlib import Path

XLSX_DIR = Path("data/xlsx")

REGIME_MAP: dict[str, str] = {
    "2020-06-30": "1",
    "2020-12-31": "1",
    "2021-06-30": "2a",
    "2021-12-31": "2a",
    "2022-06-30": "2a",
    "2022-12-31": "2a",
    "2023-06-30": "2a",
    "2023-12-31": "2b",
    "2024-06-30": "2b+",
    "2024-12-31": "2b+",
    "2025-06-30": "2b+",
    "2025-12-31": "3",
}

FOOTER_PREFIXES = ("source", "note", "1.", "2.", "3.")

# Maps APSED short agency names to the "Department of X" canonical form used by
# the gazette dataset. Names not in this table already match the gazette and are
# passed through unchanged.
_AGENCY_CANONICAL: dict[str, str] = {
    "Agriculture, Fisheries and Forestry":                                           "Department of Agriculture, Fisheries and Forestry",
    "Attorney-General's":                                                            "Attorney-General's Department",
    "Climate Change, Energy, the Environment and Water":                             "Department of Climate Change, Energy, the Environment and Water",
    "Defence":                                                                       "Department of Defence",
    "Education":                                                                     "Department of Education",
    "Employment and Workplace Relations":                                            "Department of Employment and Workplace Relations",
    "Finance":                                                                       "Department of Finance",
    "Foreign Affairs and Trade":                                                     "Department of Foreign Affairs and Trade",
    "Health and Aged Care":                                                          "Department of Health and Aged Care",
    "Home Affairs":                                                                  "Department of Home Affairs",
    "Industry, Science and Resources":                                               "Department of Industry, Science and Resources",
    "Infrastructure, Transport, Regional Development, Communications and the Arts":  "Department of Infrastructure, Transport, Regional Development, Communications and the Arts",
    "Infrastructure, Transport, Regional Development, Communications, Sport and the Arts":  "Department of Infrastructure, Transport, Regional Development, Communications and the Arts",
    "Prime Minister and Cabinet":                                                    "Department of the Prime Minister and Cabinet",
    "Social Services":                                                               "Department of Social Services",
    "Treasury":                                                                      "Department of the Treasury",
    "Veterans' Affairs":                                                             "Department of Veterans' Affairs",
    "Immigration":                                                                   "Department of Home Affairs",  # pre-MoG rename
    # Sub-agency / body name mismatches vs gazette canonical
    "Australian Trade and Investment Commission":                                     "Austrade",
    "Office of the Commonwealth Ombudsman":                                          "Commonwealth Ombudsman",
    "Office of the Fair Work Ombudsman":                                             "Fair Work Ombudsman",
    "Office of the Director of Public Prosecutions":                                 "Director of Public Prosecutions",
    "Inspector-General of Taxation":                                                 "Office of the Inspector-General of Taxation",
    "Old Parliament House":                                                          "Museum of Australian Democracy - Old Parliament House",
    "Professional Services Review":                                                  "Health Professional Services Review",
    # MoG renames now reflected in gazette data
    "Health, Disability and Ageing":                                                 "Department of Health, Disability and Ageing",
    # ── Gazette alignment fixes (apsed_agency_canonical_fixes.json) ──────────────
    # Acronyms → full names
    "AUSTRAC":                                                                       "Australian Transaction Reports and Analysis Centre",
    "GBRMPA":                                                                        "Great Barrier Reef Marine Park Authority",
    "TEQSA":                                                                         "Tertiary Education Quality and Standards Agency",
    # Punctuation / capitalisation
    "Australian Communications & Media Authority":                                   "Australian Communications and Media Authority",
    "Murray Darling Basin Authority":                                                "Murray-Darling Basin Authority",
    "National Offshore Petroleum Safety And Environmental Management Authority":     "National Offshore Petroleum Safety and Environmental Management Authority",
    # Incomplete names
    "National Film and Sound Archive":                                               "National Film and Sound Archive of Australia",
    "National Portrait Gallery":                                                     "National Portrait Gallery of Australia",
    "Aboriginal Hostels Ltd.":                                                       "Aboriginal Hostels Limited",
    # Missing "Department of" prefix
    "Agriculture, Water and the Environment":                                        "Department of Agriculture, Water and the Environment",
    "Education, Skills and Employment":                                              "Department of Education, Skills and Employment",
    "Health":                                                                        "Department of Health",
    "Infrastructure, Transport, Regional Development and Communications":            "Department of Infrastructure, Transport, Regional Development and Communications",
    "Infrastructure,Transport, Regional Development and Communications":             "Department of Infrastructure, Transport, Regional Development and Communications",
    # Agency renames
    "Asbestos Safety and Eradication Agency":                                        "Asbestos and Silica Safety and Eradication Agency",
    "Australian Sports Anti-Doping Authority":                                       "Sport Integrity Australia",
    # Entity name variants
    "Fair Work Ombudsman and Registered Organisations Commission Entity":            "Fair Work Ombudsman",
    "Federal Court Statutory Agency":                                                "Federal Court of Australia",
}


def snapshot_date_from_path(path: Path) -> str | None:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    return m.group(1) if m else None
