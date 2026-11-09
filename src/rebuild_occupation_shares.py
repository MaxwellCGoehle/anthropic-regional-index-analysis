"""
Below is a rebuild of the occupation share grouping(soc_pct) used by Anthropic in their v3 enriched release.
Rebuilds soc_pct following v3 notebook created by Anthropic, the v3 rebuild matches v3 values exactly as validation.
The method used splits tasks that have multiple major soc groups to count partly for each instead of having conversations count multiple times.
Only for v3-v5, previous versions did not have geographic breakdowns and v6 is structured seperately.
"""

from pathlib import Path
import pandas as pd

data_path = Path(__file__).resolve().parent.parent / "data"

# Store the raw files across the v3,v4, and v5
# v6 is seperate because data is structured differently will come in a seperate file
raw_files = {
    "v3": "aei_raw_claude_ai_2025-08-04_to_2025-08-11.csv",
    "v4": "aei_raw_claude_ai_2025-11-13_to_2025-11-20.csv",
    "v5": "aei_raw_claude_ai_2026-02-05_to_2026-02-12.csv",
}


# 200 conversations is the minimum value chosen by Anthropic for v3 enriched, if less the country will get dropped
# min_groups = 10 is the minimum number of major groups a country must have to be included in the baskets, chosen by me see Profile.md
min_conversations = 200  
min_groups = 10

# not_classified represents conversations hidden by privacy or could not be classified, none contains conversations with no O*NET task
# technical are the categories that are considered "technical" all other are considered "non-technical"
unassigned_labels = ["not_classified", "none"]
technical = ["Computer and Mathematical", "Life, Physical, and Social Science", "Production"]

#use version3 files to build soc_pct, this is the only release which contains the major group column
def v3_file(name):
    matches = [p for p in data_path.rglob(name) if "release_2025_09_15" in str(p)]
    return matches[0]

# tasks - contains occupations as well as major soc groups
# soc - contains the major groups like Computer and Mathematical - 15
# iso - translates countries codes, NA holds onto Namibia's country code(NA)

tasks = pd.read_csv(v3_file("onet_task_statements.csv"), dtype=str)
soc = pd.read_csv(v3_file("soc_structure.csv"), dtype=str)
iso = pd.read_csv(v3_file("iso_country_codes.csv"), dtype=str, keep_default_na=False)

tasks["task_key"] = tasks["Task"].str.lower().str.strip()

# keep only one row per task for each group, so it is not counted twice
task_groups = tasks[["task_key", "soc_major_group"]].drop_duplicates()
groups_per_task = task_groups["task_key"].value_counts()

# drop "Occupations" - matches the enriched file
# switch to 3 letter codes to match across releases
group_rows = soc.dropna(subset=["Major Group"])
titles = group_rows.set_index("soc_major_group")["SOC or O*NET-SOC 2019 Title"].str.replace(" Occupations", "")
to_iso3 = iso.set_index("iso_alpha_2")["iso_alpha_3"]

def facet_rows(df, facet, variable):
    return df[(df["facet"] == facet) & (df["variable"] == variable)]

# when split_shared=True split task evenly amongst it's groups, used for analysis
# when split_shared=False count conversation for each group it is in, used for verification
def rebuild(raw, split_shared=True):
    #drop states, non-countries, and rows like not classified or none
    countries = raw[(raw["geography"] == "country") & raw["geo_id"].isin(iso["iso_alpha_2"])]

    #keep countries above the minimum 200 conversations
    usage = facet_rows(countries, "country", "usage_count")
    kept = usage.loc[usage["value"] >= min_conversations, "geo_id"]
    print(f"countries with at least {min_conversations} conversations: {len(kept)}")

    #store the task counts for each country per task: US, write computer programs ,300
    counts = facet_rows(countries, "onet_task", "onet_task_count")
    counts = counts[counts["geo_id"].isin(kept)]

    # capture the unasigned counts and keep them to add to total, then delete them from the counts table 
    unassigned = counts[counts["cluster_name"].isin(unassigned_labels)]
    unassigned = unassigned.groupby("geo_id")["value"].sum()
    counts = counts[~counts["cluster_name"].isin(unassigned_labels)].copy()
    counts["task_key"] = counts["cluster_name"].str.lower().str.strip()

    # task that belongs to multiple groups gets a row for each group
    merged = counts.merge(task_groups, on="task_key", how="left")

    # safety measure, if not 0 then task wording does not match O*NET something has gone wrong
    no_match = merged["soc_major_group"].isna()
    unmatched = merged.loc[no_match, "value"].sum() / merged["value"].sum()
    print(f"share of task counts with no O*NET match: {unmatched:.1%}")

    # Anthropic v3 counts a task for each major group it belongs to, my method splits it evenly among it's groups
    # for instance 40 conversations split between 2 major groups would give 20 conversations to each, instead of 40 to each
    if split_shared:
       merged["value"] = merged["value"] / merged["task_key"].map(groups_per_task)
    
    by_group = merged.groupby(["geo_id", "soc_major_group"], as_index=False)["value"].sum()

    # total = each group + not_classified + none
    totals = by_group.groupby("geo_id")["value"].sum().add(unassigned, fill_value=0)
    by_group["share"] = by_group["value"] / by_group["geo_id"].map(totals) * 100

    by_group["cluster_name"] = by_group["soc_major_group"].map(titles)
    by_group["geo_id"] = by_group["geo_id"].map(to_iso3)
    return by_group.set_index(["geo_id", "cluster_name"])["share"]

#run release 3 twice, once for verification to v3 enriched numbers, once for analysis
shares = {}
for release, file_name in raw_files.items():
    print(f"\n{release}")
    raw = pd.read_csv(next(data_path.rglob(file_name)), low_memory=False, keep_default_na=False, na_values=[""])
    shares[release] = rebuild(raw)
    if release == "v3":
        v3_anthropic = rebuild(raw, split_shared=False)

# compare v3 enriched values to newly generated values
enriched = pd.read_csv(v3_file("aei_enriched_claude_ai_2025-08-04_to_2025-08-11.csv"), low_memory=False)
published = enriched[(enriched["geography"] == "country") & (enriched["variable"] == "soc_pct")]
published = published.set_index(["geo_id", "cluster_name"])["value"]

check = pd.DataFrame({"anthropic": v3_anthropic, "split": shares["v3"], "published": published}).dropna()
max_difference = (check["anthropic"] - check["published"]).abs().max()
split_difference = (check["split"] - check["published"]).abs()
print(f"\nv3 check: {len(check)} rows compared, max difference using Anthropic's method {max_difference:.4f}")
print(f"splitting shared tasks moves shares {split_difference.mean():.3f} points on average, {split_difference.max():.3f} at most")

# countries that pass conditions
print("\ncountries per release")
qualified = {}
for release, release_shares in shares.items():
    table = release_shares.unstack()
    qualified[release] = table[table.notna().sum(axis=1) >= min_groups]
    print(f"{release}: {len(table)} countries, {len(qualified[release])} with at least {min_groups} groups")

# panel contains countries that pass the minimum groups check in each release
panel = set(qualified["v3"].index)
for table in qualified.values():
    panel &= set(table.index)

# basket is the groups that every panel country has in every release
basket = set(titles)
for table in qualified.values():
    in_panel = table.loc[sorted(panel)]
    basket &= set(in_panel.dropna(axis=1).columns)

print(f"\nbasket of {len(basket)} groups")
print("technical:", sorted(basket & set(technical)))
print("non-technical:", sorted(basket - set(technical)))
print(f"countries clearing the cut in all three releases: {len(panel)}")


#Save the basket outputs for hypotheses tests
#Creates one table with 72 rows, with 7 group columns, release, and geo_id
panel_tables = []
for release, table in qualified.items():
    panel_tables.append(table.loc[sorted(panel), sorted(basket)].assign(release=release))

pd.concat(panel_tables).to_csv(data_path / "basket_shares.csv")