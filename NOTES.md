## Data Download 9/10/26
downloaded from: https://huggingface.co/datasets/Anthropic/EconomicIndex

using: hf download Anthropic/EconomicIndex --repo-type=dataset

version: release 1-6

license: CC-BY 4.0

citation: 
```
    @online{anthropic2026aeiv6,
            author = {Maxim Massenkoff and Eva Lyubich and Szymon Sacher and Zoe Hitzig and Shaoyi Zhang and Ryan Heller and Peter McCrory},
            title = {Anthropic Economic Index report: Cadences},
            date = {2026-06-26},
            year = {2026},
            url = {https://www.anthropic.com/research/economic-index-june-2026-report},
    }
```


## Initial notes after reading surrounding documentation and papers
- Data based on real Claude usage, chat interface + first party API, no conversations are human read during the analysis pipeline and PII are removed. 
- Consumer side is based on Free/Pro subscriptions with Max added in later versions. Team and Enterprise subscriptions are excluded from the datasets. (focused on individual usage vs corporate usage)
- Samples are 7 day snapshots, were changed in v6 to continuous sampling with monthly aggregation
- Geography information comes from the conversation IP, ISO codes for countries and US States, with VPN traffic being dropped to avoid issues.
- A row is a single geographic/facet combination over a set period of time, a single row contains many interactions. Underneath each conversation/prompt response pair is being classified and assigned to a bucket.
- Cells below the threshold of unique users and conversations get dropped meaning niche geographic/facet combinations may not be present by design (privacy reasons).
- Labels are a result of LLM classification, no human labeling.
- Tasks map to O*NET via a hierarchy traversal rather than direct classification.
- Categorical: collaboration mode (automation vs augmentation), use case, multitasking.
- Numerical: AI autonomy, human only time, education years. Seen in v4 and beyond.
- 6 versions at download. Geography and API split are first seen in v3, so v3-v6 will be the backbone of the analysis.
- Schema shifts between versions as well as classification modeling changes occur as well. Data integrity checks will be important when combining information from multiple versions to ensure nothing is lost or misrepresented. 

## Initial Verification for inventory purposes
- ~1M `Claude.ai` conversations in the v3 sample. Will not match as each row represents many conversations.
- ~20k O*NET task statements.
- 51 US states (50 states + DC) and 150+ countries.
- A separate labor_market_impacts folder exists within the huggingface release but does not contain geographic information, therefore is ignored in this analysis, it contains occupation level AI exposure data.

## Verification numbers chosen from the v3 report
- US is 21.6% of global Claude usage, California is 25.3% of US usage. 
- Computer and mathematical tasks are 36% of `Claude.ai` (interface based) usage and 44% of API usage.
- API traffic is 77% automation vs 12% augmentation (does not sum to 100 as some records are unclassified), `Claude.ai` is ~50% automation.

## Cross Verification from Inventory Script
| Target | Claimed | Actual | Notes |
| --- | --- | --- | --- |
| Claude AI conversations sampled | ~1M | 100k to 1.6M rows depending on release | rows are aggregated therefore dont reflect indiivdual conversations |
| O*NET task statements | ~20,000 | 19,530 across versions 1-3 | stopped shipping after v3 | 
| US States + DC | 51 | 52 in v3, 51 in v4, 54 in v5 | 51 codes are present in all three see below |
| Countries | 150+ | 172 in v3, 173 in v4, 177 in v5 | grows each release |

### Findings
- 50+ states and DC appear in each release from v3 onward - v3 introduces a not_classified bucket to make 52, v4 gets rid of that bucket to make 51, v5 adds GU, PR, and VI all US territories to make 54.
- The subnational facet is renamed after each release making the schema important to check across versions.
- Starting in v4 the subnational facet covers more than just the US making filtering for the US first neccessary.
- v6 renamed every schema column so v3-v5 will not run against it without a translation layer inbetween.
- Two files in v3's input are not parseable - population data and gdp data, both are present in the intermediate folder cleaned.
- v1 and v2 store usage in seperate wide files, one per O*NET task, their row counts are not comparable to the others, switches to a long format starting with v3.
- High missing rate in SOC structures and onet task statements are strucural. These are hierarchy files with one column per level so each row only fills the one it belongs to therefore is bvery sparse. 


## Review of several rows within the dataset and findings from them

Rows from v3 are drawn from the enriched file, a format not included in any other versions from the initial download. It holds the same sample as the raw file but adds in derived metrics such as soc_occupation facet, so the occupation level row below is not possible without using the enriched file. Provides higher level of detail that will be needed during analysis so good to have a baseline next level to compare this to other raw versions.

*v3 schema*

```
geo_id,geography,date_start,date_end,platform_and_product,facet,level,variable,cluster_name,value,geo_name
```

*v3 collaboration count line 133903* 

```
VA,state_us,2025-08-04,2025-08-11,Claude AI (Free and Pro),collaboration,0,collaboration_count,directive,3400.0,Virginia
```

Each cell in this file is described by 3 rows. The first describes total conversation count as shown above, second is a percentage of the region's conversations, the third is a specilization index which divides the regions percentages by a baseline percentage 1.0 is the baseline, above means higher usage than average and below means less. From this we can reverse engineer the total conversations of the region for that time find what clusters states are leaning into heavily vs not etc.

*v3 usage share line 135212*

```
VA,state_us,2025-08-04,2025-08-11,Claude AI (Free and Pro),state_us,0,usage_pct,,4.04418828049952,Virginia
```

Virginia accounts for 4.04% of the US total usage. Cluster_Name is empty because there is no subcategory to name, so we can see the total of all conversations not limited to a specific category. This is an important understanding for which states are leading in usage or which states are using Claude more than their population or other factors may suggest they would be.


*v3 unclassified tasks line 134074*

```
VA,state_us,2025-08-04,2025-08-11,Claude AI (Free and Pro),onet_task,0,onet_task_count,not_classified,3596.0,Virginia
```

Virginia is shown to have 3,596 conversations that were not classified to an O*NET task, this is higher than the entire directive count shown above during the same time frame. This points to the fact that these conversations cannot be ignored they represent a large portion of the dataset and include meaningful information but need to be treated different than those that are classified. 

*v3 occupation share line 135192*

```
VA,state_us,2025-08-04,2025-08-11,Claude AI (Free and Pro),soc_occupation,0,soc_pct,Architecture and Engineering,0.5687203791469195,Virginia
```

Virginia's conversations based in Architecture and Engineering took up merely 0.57% of the states classified conversations. This is an important note because as we have shown previously 3,596 conversations were not classified during this timeframe, meaning this 0.57% is not the number of total conversations the true percentage is less. This metric is added through the enrichment process in v3 and proves to provide meaningful information that may be useful to derive in other releases through O*NET tasks being labeled to SOC major groups. 


*v4 and v5 schema*

```
geo_id,geography,date_start,date_end,platform_and_product,facet,level,variable,cluster_name,value
```

*v4 AI autonomy line 454923*
```
US-VA,country-state,2025-11-13,2025-11-20,Claude AI (Free and Pro),ai_autonomy,0,ai_autonomy_mean,,3.2857894897460938
```

Now looking at a v4 output we can see the code for Virginia has changed to US-VA instead of VA, in addition the format from v3 of count, percent of region usage, then percent of greater geographic region has been changed to count, mean, median, standard deviation, and confidence intervals. In addition we can see that the cluster_name is null here because the autonomy is numeric rather than categorical. We also can see that Virginia's mean autonomy is 3.29 which exists on a scale of 1 to 5. 

*v5 AI autonomy line 475280* 

```
US-VA,country-state,2026-02-05,2026-02-12,"Claude AI (Free, Pro, and Max)",ai_autonomy,0,ai_autonomy_mean,,3.307816505432129
```

Now looking at v5 output of the same measure we can see that the Claude AI Max plan has now been added to the dataset, otherwise we see an identical setup. During this period of time Virginia's mean autonomy is 3.31 very close to the number found from v4 indicating this number is probably steady even with the new population change of adding Max users. This will be an area to explore across states and periods of time to see if over time there have been changes in overall workflow and especially in certain regions.

*v6 schema*

```
date_start,date_end,geo_id,geo_level,category_name,hierarchy_level,metric_id,value,node_name,node_external_id
```

*v6 artifact analysis line 5983*

```
2026-05-01,2026-06-01,US-VA,subregion,overall,0,artifact_analysis_or_summary_pct,5.78,Overall,-
```

At first glance we can see a big schema change in how the features are presented we see the window is now monthly vs weekly in previous releases, and multiple columns have undergone name changes. In addition to these name changes platform_and_product is dropped noted by the files themselves,  node_external_id is added which is noted by a - in this specific row but provides O*NET codes on occupation rows and UUIDs on request rows making mapping easier. Ensuring smooth transition across schemas will be important when looking at overall changes whether combining previous releases into a more monthly friendly format or keeping the two distinct the way they currently are is a design choice. This row itself says that 5.78% of Virginia conversations in May of 2026 resulted in an artifact analysis or summary. 
