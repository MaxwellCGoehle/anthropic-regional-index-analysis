"""
Exploratory analysis based on the v3 enriched file only. 
"""

import argparse
import sys
from pathlib import Path
import matplotlib.pyplot as plt
from scipy.stats import linregress
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Exploratory analysis for PROFILE.md.")
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

    #keep only states, create one column per state
    states_df = v3_df[(v3_df.geography == "state_us") & (v3_df.geo_id != "not_classified")]
    pivot = states_df.pivot_table(index="geo_id", columns="variable", values="value")

    aui = pivot["usage_per_capita_index"]
    automation = pivot["automation_pct"]
    augmentation = pivot["augmentation_pct"]
    gdp = pivot["gdp_per_working_age_capita"]
    counts = pivot["usage_count"]

    #AUI plot
    fig, axis = plt.subplots()
    axis.hist(aui, bins=20)
    axis.set_title("Distribution of the Per Capita Index by State")
    axis.set_xlabel("usage share divided by working age population share")
    axis.set_ylabel("number of states")
    fig.savefig(exploratory_figures / "aui_distribution.png")

    #Automation plot
    fig, axis = plt.subplots()
    axis.hist(automation, bins=20)
    axis.set_title("Distribution of automation by State")
    axis.set_xlabel("percent of classified conversations that are automation")
    axis.set_ylabel("number of states in bucket")
    fig.savefig(exploratory_figures / "automation_distribution.png")

    #How gdp and aui relate using simple linear regression
    fit = linregress(gdp, aui)


    #GDP and AUI SLR plot
    fig, axis = plt.subplots()
    axis.scatter(gdp,aui)
    axis.plot(gdp, fit.slope * gdp + fit.intercept, color="black")
    axis.set_title("Per capita adoption vs state GDP")
    axis.set_xlabel("GDP per working age capita")
    axis.set_ylabel("usage per capita index")
    fig.savefig(exploratory_figures / "aui_vs_gdp.png") 

    print(f"Wrote 3 figures to {exploratory_figures}")  

    print("\nHighest Adoption by AUI")
    print(aui.sort_values(ascending=False).head(5).round(2).to_string())
    print("\nLowest Adoption by AUI")
    print(aui.sort_values(ascending=True).head(5).round(2).to_string())

    print("\nAutomation Leaders")
    print(automation.sort_values(ascending=False).head(4).round(1).to_string())
    print("\nAugmentation Leaders")
    print(augmentation.sort_values(ascending=False).head(4).round(1).to_string())

    print("\nSmallest Sample Size")
    print(counts.sort_values(ascending=True).head(4).astype(int).to_string())

    #DC and UTAH are major outliers in the GDP vs AUI regression, look at r's without the 2 biggest outliers
    print(f"\nr with all states {fit.rvalue:.2f}")
    print(f"r without DC: {aui.drop('DC').corr(gdp.drop('DC')):.2f}")
    print(f"r without UT: {aui.drop('UT').corr(gdp.drop('UT')):.2f}")

if __name__ == "__main__":
    main()