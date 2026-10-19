"""
Looking at how much of each country's usage is non technical work
"""

import argparse
import sys
from pathlib import Path
from scipy.stats import linregress
import pandas as pd
import requests

#Update WB naming to be easier
indicators = {
    "NY.GDP.PCAP.CD": "gdp_per_capita",
    "SP.POP.TOTL": "population",
    "SL.SRV.EMPL.ZS": "services_employment_pct",
    "SE.TER.ENRR": "tertiary_enrollment",
}

#Services, tertiary to represent workforce, gdp and developers because they have been the baseline
covariates = ["gdp_per_capita", "developers_per_100k", "services_employment_pct", "tertiary_enrollment"]

#Computer, science and production, everything else counts as non technical
technical = ["Computer and Mathematical", "Life, Physical, and Social Science", "Production"]

wdi_url = "https://api.worldbank.org/v2/country/all/indicator/{code}"
country_url = "https://api.worldbank.org/v2/country"
github_url = "https://raw.githubusercontent.com/github/innovationgraph/main/data/developers.csv"

#Capture same timeframe as v3 data
github_year = 2025
github_quarter = 3

#10 keeps a decent number of countries without the shared basket getting too thin
min_occupations = 10

def main():
    parser = argparse.ArgumentParser(description="Non technical share of usage across countries.")
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

    #Combine on country codes
    joined["developers"] = github["developers"]

    #Change GitHub data to rate
    joined["developers_per_100k"] = joined["developers"] / joined["population"] * 100000

    #Usage by SOC occupation group, classified off the task rather than the user's job
    soc = v3_df[(v3_df.geography == "country") & (v3_df.variable == "soc_pct")]
    shares = soc.pivot_table(index="geo_id", columns="cluster_name", values="value")

    #not_classified is usage that got censored, not usage that is non technical, so it cannot stay in the denominator
    occupations = shares.drop(columns="not_classified")

    #Occupations too small to publish get pooled into not_classified
    joined["occupations_reported"] = occupations.notna().sum(axis=1)

    #A country with only computer work left reads as 0% non technical
    joined["raw_share"] = occupations.drop(columns=technical).sum(axis=1) / occupations.sum(axis=1) * 100

    reporting = joined[joined["occupations_reported"] > 0]

    print(f"countries reporting occupations: {len(reporting)}")
    print(f"raw non technical share vs conversations, spearman {reporting['raw_share'].corr(reporting['usage_count'], method='spearman'):.2f}")

    print("\nRaw Non Technical Share by How Many Occupations Survived")
    print(reporting.groupby("occupations_reported").agg(
        countries=("raw_share", "count"),
        median_share=("raw_share", "median"),
        median_conversations=("usage_count", "median"),
    ).round(1).to_string())

    #Raising the cut keeps fewer countries, lowering it leaves fewer occupations they all share
    print("\nWhere to Cut")
    for threshold in (5, 8, 10, 13):
        kept = reporting[reporting["occupations_reported"] >= threshold]
        common = occupations.loc[kept.index].dropna(axis=1)
        print(f"at least {threshold}: {len(kept)} countries, {len(common.columns)} occupations in common")

    usable = reporting[reporting["occupations_reported"] >= min_occupations].copy()

    #Every country left reports all of these so they get the same denominator
    basket = occupations.loc[usable.index].dropna(axis=1)
    usable["non_technical_share"] = basket.drop(columns=technical).sum(axis=1) / basket.sum(axis=1) * 100

    print(f"\nBasket of {len(basket.columns)} occupations all {len(usable)} countries report")
    print(", ".join(basket.columns))

    print("\nNon Technical Share Within the Basket")
    print(usable["non_technical_share"].describe().round(1).to_string())
    print(f"vs conversations, spearman {usable['non_technical_share'].corr(usable['usage_count'], method='spearman'):.2f}")

    print("\nNon Technical Share Within the Basket")
    print(usable["non_technical_share"].describe().round(1).to_string())
    print(f"vs conversations, spearman {usable['non_technical_share'].corr(usable['usage_count'], method='spearman'):.2f}")

    #Pooled across the 28 so bigger countries count for more, one number to track across releases
    basket_counts = basket.multiply(usable["usage_count"], axis=0)
    pooled = basket_counts.drop(columns=technical).sum().sum() / basket_counts.sum().sum() * 100

    print(f"pooled across all {len(usable)} countries, {pooled:.1f}")

    print("\nBaseline, Most to Least Non Technical")
    print(usable.sort_values("non_technical_share", ascending=False)[["non_technical_share", "automation_pct", "usage_count"]].round(1).to_string())

    print("\nWhat Goes With a Higher Non Technical Share")
    print(usable[covariates].corrwith(usable["non_technical_share"], method="spearman").round(2).to_string())

    #Coding work is more automatable so a higher non technical share should mean less automation
    automation_model = usable[["automation_pct", "non_technical_share"]].dropna()
    fit = linregress(automation_model["non_technical_share"], automation_model["automation_pct"])

    print(f"\nAutomation Against Non Technical Share, {len(automation_model)} countries")
    print(f"r2 {fit.rvalue ** 2:.2f}, slope {fit.slope:.2f}, p {fit.pvalue:.3f}")

if __name__ == "__main__":
    main()