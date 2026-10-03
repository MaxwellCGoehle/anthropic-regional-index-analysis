"""
Exploratory analysis using world bank and github data
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import requests

#Update WB naming to be easier
indicators = {
    "IT.NET.USER.ZS": "internet_pct",
    "SE.TER.ENRR": "tertiary_enrollment",
    "SL.SRV.EMPL.ZS": "services_employment_pct",
    "SP.URB.TOTL.IN.ZS": "urban_pct",
    "SI.POV.GINI": "gini_index",
    "NY.GDP.PCAP.CD": "gdp_per_capita",
    "SP.POP.TOTL": "population",
}

outcomes = ["usage_per_capita_index", "automation_pct", "usage_count"]

wdi_url = "https://api.worldbank.org/v2/country/all/indicator/{code}"
country_url = "https://api.worldbank.org/v2/country"
github_url = "https://raw.githubusercontent.com/github/innovationgraph/main/data/developers.csv"

#Capture same timeframe as v3 data
github_year = 2025
github_quarter = 3

def main():
    parser = argparse.ArgumentParser(description="Compare outside sources to v3 data.")
    parser.add_argument("--data", default="data", help="data directory (default: ./data)")
    args = parser.parse_args()

    data_dir = Path(args.data).expanduser().resolve()

    #Avoid huggingface hash
    v3_enriched_csv = next(data_dir.rglob("*enriched_claude_ai*.csv"), None)
    if v3_enriched_csv is None:
        sys.exit(f"v3_enriched_csv not found in {data_dir}")
    v3_df = pd.read_csv(v3_enriched_csv, low_memory=False)

    countries_df = v3_df[(v3_df.geography == "country") & (v3_df.geo_id != "not_classified")]
    countries = countries_df.pivot_table(index="geo_id", columns="variable", values="value")
    countries = countries[countries["usage_count"] > 0]

    #One call per indicator
    world_bank = []
    for code, name in indicators.items():
        response = requests.get(wdi_url.format(code=code),
                                params={"format": "json", "date": "2015:2024", "per_page": 20000},
                                timeout=60)
        response.raise_for_status()

        #1st index is just paging info
        rows = pd.DataFrame(response.json()[1])
        rows = rows[["countryiso3code", "date", "value"]].dropna(subset=["value"])
        rows = rows[rows["countryiso3code"] != ""]
        rows["date"] = rows["date"].astype(int)

        #Coverage is scarce so just keep latest of each country
        rows = rows.sort_values("date").groupby("countryiso3code").last()
        world_bank.append(rows["value"].rename(name))

    joined = countries.join(pd.concat(world_bank, axis=1))

    #Get country list for GitHub data
    response = requests.get(country_url, params={"format": "json", "per_page": 400}, timeout=60)
    response.raise_for_status()

    iso_codes = pd.DataFrame(response.json()[1])
    iso_codes["region"] = iso_codes["region"].apply(lambda region: region["id"])
    iso_codes = iso_codes[iso_codes["region"] != "NA"].set_index("iso2Code")["id"]

    #Drop non country data because github mixes it in like "EU"
    github = pd.read_csv(github_url)
    github = github[(github.year == github_year) & (github.quarter == github_quarter)]
    github["geo_id"] = github["iso2_code"].map(iso_codes)
    github = github.dropna(subset=["geo_id"]).set_index("geo_id")

    #Combine based on country codes
    joined["developers"] = github["developers"]

    #Change GitHub data to rate
    joined["developers_per_100k"] = joined["developers"] / joined["population"] * 100000

    sources = {name: "world bank" for name in indicators.values()}
    sources["developers_per_100k"] = "github"
    columns = list(sources)

    coverage_rows = []
    for name in columns:
        coverage_rows.append({
            "variable": name,
            "source": sources[name],
            "matched": int(joined[name].notna().sum()),
            "missing": int(joined[name].isna().sum()),
        })
    coverage = pd.DataFrame(coverage_rows).sort_values("matched", ascending=False)

    print(f"countries with usage: {len(countries)}\n")
    print("Coverage")
    print(coverage.to_string(index=False))

    #Spearman correlation to avoid skew issues
    correlations = joined[outcomes + columns].corr(method="spearman")

    print("\nCorrelation with Adoption Numbers")
    print(correlations.loc[columns, outcomes].round(2).to_string())

    #How much usage a country gets based on the size of its developer base
    developer_usage = joined.dropna(subset=["usage_count", "developers"])
    usage_share = developer_usage["usage_count"] / developer_usage["usage_count"].sum()
    developer_share = developer_usage["developers"] / developer_usage["developers"].sum()
    joined["ratio"] = usage_share / developer_share

    #Drop low usage countries for now
    ranked = joined.dropna(subset=["ratio"])
    ranked = ranked[ranked["usage_count"] >= 100]

    print(f"\nUsage Per Developer Base, {len(ranked)} countries over 100 conversations")
    print(ranked.sort_values("ratio", ascending=False)[["ratio", "usage_count"]].head(5).round(2).to_string())
    print("\nLowest")
    print(ranked.sort_values("ratio")[["ratio", "usage_count"]].head(5).round(2).to_string())

if __name__ == "__main__":
    main()