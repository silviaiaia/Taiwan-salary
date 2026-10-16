"""Build a consistent occupation-by-year salary table from the raw MOL survey files.

Source: Ministry of Labor (Taiwan), Occupational Wage Survey, July regular earnings,
electronic components manufacturing. One Excel file per survey year (ROC 110-113,
i.e. 2021-2024) in data/raw/.

What this script does:
1. Reads each raw file and extracts the 6-digit occupation code, the Chinese
   occupation name and the July regular monthly earnings.
2. Treats "-" and "---" as missing. The survey suppresses values where the
   sample is too small to publish.
3. Maps every year onto the 28 occupation categories used in the 2022-2024
   surveys. The 2021 survey split several of these into finer categories, so
   those are combined with a simple (unweighted) mean, rounded down to the
   whole dollar. The survey does not publish headcounts, so a weighted mean
   is not possible.
4. Writes data/processed/salary_benchmark.csv.
"""

import math
import re
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
OUT_PATH = Path("data/processed/salary_benchmark.csv")

# The 28 benchmark occupations, keyed by the code used in the 2022-2024 surveys.
OCCUPATIONS = {
    "112000": "Senior executives (general managers and CEOs)",
    "120090": "Middle managers",
    "312190": "Supervisors (site and office supervisors, section heads)",
    "214100": "Quality, industrial and production engineers",
    "215190": "Electrical and electronics engineers",
    "217300": "Product and garment designers (incl. industrial design)",
    "241100": "Accountants and auditors",
    "242100": "Project managers (incl. management consultants)",
    "243100": "Advertising and marketing professionals",
    "250000": "ICT professionals (systems analysis, programming, database and network)",
    "311390": "Electrical and electronics technicians",
    "311700": "Quality, industrial and production technicians",
    "331300": "Accounting associates",
    "332290": "Sales representatives",
    "332300": "Purchasing officers",
    "334200": "Executive secretaries",
    "341191": "Legal associates",
    "351090": "IT operations and support technicians",
    "411002": "General affairs clerks",
    "411090": "General office clerks (incl. data entry)",
    "422290": "Receptionists and information desk clerks (incl. switchboard)",
    "431100": "Bookkeeping and payroll clerks",
    "432100": "Stock clerks",
    "432200": "Production and material planning clerks",
    "491000": "Human resources clerks",
    "810090": "Production machine operators",
    "820000": "Assemblers",
    "820001": "Semiconductor production line operators",
}

# Occupation groups follow the first digit of the code (the survey's major groups),
# except that supervisors (312190) are grouped with managers.
MANAGERS = {"112000", "120090", "312190"}
GROUPS = {
    "2": "Professionals",
    "3": "Technicians and associate professionals",
    "4": "Clerical support",
    "8": "Machine operators and assemblers",
}

# 2021 categories that differ from 2022-2024. Every other code is the same in all years.
# Key: benchmark code. Value: the 2021 codes combined into it.
CODE_MAP_2021 = {
    "214100": ["214102", "214191"],            # QC engineers + industrial/production engineers
    "215190": ["215100", "215200"],            # electrical + electronics engineers
    "250000": ["251100", "251290", "252090"],  # systems analysts + software developers + database/network
    "311390": ["311300", "311400"],            # electrical + electronics technicians
    "311700": ["311702", "311791"],            # QC technicians + industrial/production technicians
    "411090": ["411090", "413000"],            # general office clerks + data entry clerks
    "422290": ["422200", "422300"],            # receptionists + switchboard operators
    "810090": ["814291", "819300"],            # plastic product + packaging machine operators (approximation)
    "820001": ["819901"],                      # semiconductor machine operators (renamed)
}


def occupation_group(code: str) -> str:
    return "Managers and supervisors" if code in MANAGERS else GROUPS[code[0]]


def read_survey(path: Path) -> tuple[int, str, pd.DataFrame]:
    """Return (year, population label, table of code / name / salary) for one raw file."""
    roc_year = int(re.search(r"(\d+)年", path.name).group(1))
    raw = pd.read_excel(path, header=None)
    title = str(raw.iloc[0, 0])
    population = "Full-time employees" if "全時" in title else "All employees"

    rows = []
    for label, value in raw.iloc[3:, :2].itertuples(index=False):
        match = re.search(r"\((\d{6})\)(.+)", str(label).replace("　", "").strip())
        if not match:
            continue
        text = str(value).replace(",", "").strip()
        salary = int(float(text)) if re.fullmatch(r"\d+(\.\d+)?", text) else None  # "-" / "---" -> None
        rows.append({"code": match.group(1), "name_zh": match.group(2).strip(), "salary": salary})

    return roc_year + 1911, population, pd.DataFrame(rows).set_index("code")


def build() -> pd.DataFrame:
    records = []
    for path in sorted(RAW_DIR.glob("*.xlsx")):
        year, population, survey = read_survey(path)
        for code, name_en in OCCUPATIONS.items():
            sources = CODE_MAP_2021.get(code, [code]) if year == 2021 else [code]
            values = [survey.loc[c, "salary"] for c in sources]
            if any(v is None or pd.isna(v) for v in values):
                raise ValueError(f"{year} {code}: missing value in source codes {sources}")
            salary = math.floor(sum(values) / len(values))
            name_zh = survey.loc[code, "name_zh"] if code in survey.index else None
            records.append({
                "year": year,
                "occupation_code": code,
                "occupation_en": name_en,
                "occupation_zh": name_zh,
                "occupation_group": occupation_group(code),
                "monthly_salary_twd": salary,
                "source_codes": "+".join(sources),
                "survey_population": population,
            })

    table = pd.DataFrame(records)
    # Use the latest survey's Chinese name for every year so each occupation has one label.
    latest = table[table.year == table.year.max()].set_index("occupation_code")["occupation_zh"]
    table["occupation_zh"] = table["occupation_code"].map(latest)
    return table.sort_values(["year", "occupation_code"]).reset_index(drop=True)


if __name__ == "__main__":
    result = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT_PATH, index=False, encoding="utf-8")
    print(f"Wrote {len(result)} rows to {OUT_PATH}")
