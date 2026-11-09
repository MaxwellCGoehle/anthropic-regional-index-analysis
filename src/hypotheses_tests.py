"""
Hypotheses from PROFILE.md 

Tests H1, H3 
H2 not tested yet

"""
from pathlib import Path
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

data_path = Path(__file__).resolve().parent.parent / "data"
figures_path = Path(__file__).resolve().parent.parent / "figures"

basket_shares = pd.read_csv(data_path / "basket_shares.csv", index_col="geo_id")

basket_technical_groups = ["Computer and Mathematical", "Life, Physical, and Social Science"]
# Production is technical but not in the basket for v3-v5
technical_groups = basket_technical_groups + ["Production"]

# Hypothesis 1
# compute non-technical share, which is everything excpet the 2 technical groups
# Production not here as it is not in the basket
basket_total = basket_shares.drop(columns="release").sum(axis=1)
basket_technical = basket_shares[basket_technical_groups].sum(axis=1)
basket_shares["non_tech_share"] = (basket_total - basket_technical) / basket_total * 100

v3_non_tech_share = basket_shares.loc[basket_shares['release'] == 'v3', 'non_tech_share']
v4_non_tech_share = basket_shares.loc[basket_shares['release'] == 'v4', 'non_tech_share']
v5_non_tech_share = basket_shares.loc[basket_shares['release'] == 'v5', 'non_tech_share']

#compute the wilcoxon test for the hypothesis in addition to some descriptive statistics
h1_results = stats.wilcoxon(v5_non_tech_share - v3_non_tech_share)
print(f"H1 Wilcoxon test: statistic = {h1_results.statistic}, pvalue = {h1_results.pvalue:.2e}, n = {len(v5_non_tech_share)}")
print(f"Median change from v3 to v5: {(v5_non_tech_share - v3_non_tech_share).median():.3f}")

print(basket_shares.groupby("release")["non_tech_share"].median())
print(f"Median change from v3 to v4: {(v4_non_tech_share - v3_non_tech_share).median():.3f}")
print(f"Median change from v4 to v5: {(v5_non_tech_share - v4_non_tech_share).median():.3f}")
print(f"Number of countries with increase from v3 to v4: {(v4_non_tech_share - v3_non_tech_share > 0).sum()}")
print(f"Number of countries with increase from v4 to v5: {(v5_non_tech_share - v4_non_tech_share > 0).sum()}")
print(f"Number of countries with increase from v3 to v5: {(v5_non_tech_share - v3_non_tech_share > 0).sum()}")


group_columns = basket_shares.columns.drop(["release", "non_tech_share"])
group_share = basket_shares[group_columns].div(basket_total, axis=0) * 100

v3_group_share = group_share[basket_shares['release'] == 'v3']
v5_group_share = group_share[basket_shares['release'] == 'v5']

print(f"Median change by group from v3 to v5:\n {(v5_group_share - v3_group_share).median().sort_values()}")

# one line per country across the releases
non_tech_by_release = basket_shares.reset_index().pivot(index="geo_id", columns="release", values="non_tech_share")
release_medians = non_tech_by_release.median()

fig, ax = plt.subplots(figsize=(6, 5))

for _, row in non_tech_by_release.iterrows():
    ax.plot([0, 1, 2], row[["v3", "v4", "v5"]], color="gray", linewidth=1)

# show the median of all countries
ax.plot([0, 1, 2], release_medians[["v3", "v4", "v5"]], color="blue", linewidth=2, marker="o")

ax.set_xticks([0, 1, 2], ["v3\nAug 2025", "v4\nNov 2025", "v5\nFeb 2026"])
ax.set_ylabel("Non-Technical share of basket %")
ax.set_title("Non-Technical share rose in all 24 countries")

fig.savefig(figures_path/"result_figures" / "h1_slope.png", dpi=200, bbox_inches="tight")


# Hypothesis 2:
# ICT employment share is correlated with non-technical share
# Not Yet Tested



# Hypothesis 3:
# Services employment share is correlated with non-technical share

v6_path = list(data_path.rglob("aei_claude_ai_2026-06-26.csv"))[0]
v6 = pd.read_csv(v6_path, low_memory=False)

# only hold May values, since 2 months are in v6
v6_may = v6[v6["date_start"] == "2026-05-01"]
v6_may = v6_may[v6_may["geo_level"] == "country"]
v6_may = v6_may[(v6_may["category_name"] == "soc_occupation") & (v6_may["hierarchy_level"] == 1) & (v6_may["metric_id"] == "pct")]


# row: each country, column: each group
v6_shares = v6_may.pivot(index="geo_id", columns="node_name", values="value")

v6_total = v6_shares.sum(axis=1)
v6_technical = v6_shares[technical_groups].sum(axis=1)
v6_non_tech_share = (v6_total - v6_technical) / v6_total * 100

employment = pd.read_csv(data_path / "country_panel.csv", index_col="geo_id")

# non-tech share : services_employment
share_vs_services = pd.DataFrame({
    "non_tech_share": v6_non_tech_share,
    "services_employment": employment["services_employment_pct"],
}).dropna()

h3_results = stats.spearmanr(share_vs_services["non_tech_share"], share_vs_services["services_employment"])
print(f"H3 services employment: ρ = {h3_results.statistic:.3f}, pvalue = {h3_results.pvalue:.6f}, n = {len(share_vs_services)}")

v6_without_production = (v6_total - v6_shares[basket_technical_groups].sum(axis=1)) / v6_total * 100
print(f"H3 without Production: ρ = {stats.spearmanr(v6_without_production.loc[share_vs_services.index], share_vs_services['services_employment']).statistic:.3f}")