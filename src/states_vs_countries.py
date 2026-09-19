"""
Comparing states against countries in the v3 enriched, to decide which would be better for long term analysis.
"""

import argparse
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Compare state and country levels for PROFILE.md.")
    parser.add_argument("--data", default="data", help="data directory (default: ./data)")
    args = parser.parse_args()

    data_dir = Path(args.data).expanduser().resolve()
    exploratory_figures = Path("figures/exploratory_figures")
    exploratory_figures.mkdir(parents=True, exist_ok=True)

    #Avoid huggingface hash
    v3_enriched_csv = next(data_dir.rglob("*enriched_claude_ai*.csv"))
    if v3_enriched_csv is None:
        sys.exit(f"v3_enriched_csv not found in {data_dir}")
    v3_df = pd.read_csv(v3_enriched_csv, low_memory=False)

    #same pivot for both levels, one row per geography and one column per variable
    states_df = v3_df[(v3_df.geography == "state_us") & (v3_df.geo_id != "not_classified")]
    countries_df = v3_df[(v3_df.geography == "country") & (v3_df.geo_id != "not_classified")]

    states = states_df.pivot_table(index="geo_id", columns="variable", values="value")
    countries = countries_df.pivot_table(index="geo_id", columns="variable", values="value")

    #some countries have information in the set but no usage
    states = states[states["usage_count"] > 0]
    countries = countries[countries["usage_count"] > 0]

    state_aui = states["usage_per_capita_index"]
    state_automation = states["automation_pct"]
    state_gdp = states["gdp_per_working_age_capita"]
    state_counts = states["usage_count"]

    country_aui = countries["usage_per_capita_index"]
    country_automation = countries["automation_pct"]
    country_gdp = countries["gdp_per_working_age_capita"]
    country_counts = countries["usage_count"]

    #two panels: one for states, and one for countries
    fig, (states_axis, countries_axis) = plt.subplots(2, 1, sharex=True)

    states_axis.hist(state_aui, bins=20)
    states_axis.set_title("Per Capita Index, States vs Countries")
    states_axis.set_ylabel("number of states")

    countries_axis.hist(country_aui, bins=20)
    countries_axis.set_ylabel("number of countries")
    countries_axis.set_xlabel("usage share divided by working age population share")

    fig.savefig(exploratory_figures / "states_vs_countries.png")

    print(f"Wrote 1 figure to {exploratory_figures}")

    print("\nPer Capita Index")
    print(pd.DataFrame({"states": state_aui.describe(),
                        "countries": country_aui.describe()}).round(2).to_string())

    print("\nAutomation Share")
    print(pd.DataFrame({"states": state_automation.describe(),
                        "countries": country_automation.describe()}).round(2).to_string())

    print("\nConversations")
    print(pd.DataFrame({"states": state_counts.describe(),
                        "countries": country_counts.describe()}).round(0).to_string())

    print(f"\nIndex vs GDP, states {state_aui.corr(state_gdp):.2f}, countries {country_aui.corr(country_gdp):.2f}")

    print("\nHighest Adoption Countries")
    print(country_aui.sort_values(ascending=False).head(5).round(2).to_string())
    print("\nLowest Adoption Countries")
    print(country_aui.sort_values(ascending=True).head(5).round(2).to_string())

    #the 0% and 100% automation countries are all tiny, censored modes get pooled into not_classified
    #check sample sizes here as is an important issue to look at
    extremes = countries[(country_automation == 0) | (country_automation == 100)]
    print("\nCountries at 0% or 100% Automation")
    print(extremes[["usage_count", "automation_pct"]].round(1).to_string())

    ranked = countries[["usage_per_capita_index", "usage_count"]].dropna()

    print("\nHighest Adoption Countries")
    print(ranked.sort_values("usage_per_capita_index", ascending=False).head(5).round(2).to_string())
    print("\nLowest Adoption Countries")
    print(ranked.sort_values("usage_per_capita_index", ascending=True).head(5).round(2).to_string())

if __name__ == "__main__":
    main()