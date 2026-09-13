"""
Inventory of the data downloaded from the Anthropic Economic Index
"""

import argparse
import sys
from pathlib import Path
import pandas as pd

file_types = {".csv", ".tsv", ".json"}

#Nested Trees are skipped as data is already present in CSVs
skip_files = {"release_2025_09_15/data/output/request_hierarchy_tree_1p_api.json", "release_2025_09_15/data/output/request_hierarchy_tree_claude_ai.json"}

#State facets is renamed throughout release, ensure all are caught
state_facets = {"state_us", "country-state"}


def build_inventory(data_dir):
    file_table = []
    column_table = []

    for path in sorted(data_dir.rglob("*")):
        if not path.is_file() or path.suffix not in file_types:
            continue

        #Trim off huggingface hash
        name = str(path.relative_to(data_dir))
        for folder in ("release_", "labor_market_impacts"):
            if folder in name:
                name = name[name.index(folder):]
                break

        file_info = {
            "file": name,
            "size_mb": round(path.stat().st_size / (1024 * 1024), 2),
            "rows": None,
            "columns": None,
            "note": None
        }

        if name in skip_files:
            file_info["note"] = "skipped: nested tree"
            file_table.append(file_info)
            continue

        try:
            if path.suffix == ".csv":
                df = pd.read_csv(path, low_memory=False)
            if path.suffix == ".json":
                df = pd.read_json(path)
            if path.suffix == ".tsv":
                df = pd.read_csv(path, sep="\t", low_memory=False)

        #Two of the source files do not parse just note them and keep moving, are part of the v3 release
        except Exception:
            file_info["note"] = "skipped: ParseError - is expected"
            file_table.append(file_info)
            continue

        file_info["rows"] = len(df)
        file_info["columns"] = len(df.columns)
        file_table.append(file_info)

        for column in df.columns:
            column_table.append({
                "file": name,
                "column": column,
                "dtype": str(df[column].dtype),
                "missing_rate": round(df[column].isna().mean(), 4)
            })

    return pd.DataFrame(file_table), pd.DataFrame(column_table)

def targets_vs_baseline(data_dir):
    releases = []

    for release in sorted( p for p in data_dir.rglob("release_*") if p.is_dir()):
        release_info = {
            "release" : release.name,
            "rows": None,
            "states": None,
            "countries": None,
            "onet_tasks": None,
            "note": None
        }

        task_files = next(release.rglob("onet_task_statements.csv"), None)
        if task_files:
            release_info["onet_tasks"] = len(pd.read_csv(task_files, low_memory=False))

        #The usage file is named differently in every release, enriched copy is skipped since v3 is only one with it
        #Wide task files v1/v2 are not comparable to other releases long format
        usage_files = [p for p in release.rglob("*claude_ai*.csv") if "enriched" not in p.name]
        if not usage_files:
            usage_files = sorted(release.rglob("task_pct*.csv"))
        if not usage_files:
            usage_files = sorted(release.rglob("onet_task_mappings.csv"))
        if not usage_files:
            release_info["note"] = "no usage file found"
            releases.append(release_info)
            continue

        usage = pd.read_csv(usage_files[0], low_memory=False)
        release_info["rows"] = len(usage)

        if {"facet", "geo_id"}.issubset(usage.columns):
            #handle schema changes and drop everything that is not US states
            states = usage.loc[usage["facet"].isin(state_facets), "geo_id"].dropna()
            if states.str.startswith("US-").any():
                states = states[states.str.startswith("US-")]

            release_info["states"] = states.nunique()
            release_info["countries"] = usage.loc[usage["facet"] == "country", "geo_id"].nunique()
        elif "geo_level" in usage.columns:
            release_info["note"] = "v6 renamed the schema columns"
        else:
            release_info["note"] = "wide format, rows not comparable"

        releases.append(release_info)

    return pd.DataFrame(releases)


def main():
    parser = argparse.ArgumentParser(description="Inventory the Anthropic Economic Index data.")
    parser.add_argument("--data", default="data", help="Path to data directory /data is default")
    args = parser.parse_args()

    data_dir = Path(args.data).expanduser().resolve()
    if not data_dir.is_dir():
        sys.exit(f"not a directory: {data_dir}")

    files, columns = build_inventory(data_dir)

    #One row per file
    by_file = columns.groupby("file").agg(
        columns= ("column", "count"),
        dtypes = ("dtype", lambda s: ", ".join(sorted(set(s)))),
        missing_columns = ("missing_rate", lambda s: (s > 0).sum()), 
        worst_missing_rate = ("missing_rate", "max")
    ).reset_index()

    print(f"data directory: {data_dir}\n")

    print("File Inventory:")
    print(files.to_string(index=False))

    print("\nColumn Inventory")
    print(by_file.sort_values("worst_missing_rate", ascending=False).to_string(index=False))

    print("\nTotals")
    print(f"Total files: {len(files)}")
    print(f"Total rows: {files['rows'].sum()}")
    print(f"Total columns: {len(columns)}")
    print(f"Total skipped: {files['note'].notna().sum()}")

    print("\nClaimed vs Noted Targets")
    print("claimed: ~1M conversations sampled, ~20,000 O*NET task statements")
    print("51 US states(50 states + DC) and 150+ countries")
    print()
    print(targets_vs_baseline(data_dir).to_string(index=False))


if __name__ == "__main__":
    main()