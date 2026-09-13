# Profile.md

All figures and numbers were calculated using the v3 enriched file, covering August 4-11 of 2025. Figures and numbers are calculated in exploratory_analysis.py

I am using research Q2: What explains geographic differences in AI adoption. We have two main factors here included within v3 that should provide some insight: per capita index and the automation share. Both are defined to the state level, and are added during enrichment meaning derived attributes that are not present in other versions, so initial exploration will decide if exploring these factors in other releases would be a good idea.

## Per Capita Adoption

![AUI distribution](figures/exploratory_figures/aui_distribution.png)

This index is a state's share of US usage divided by the states share of the working age population. This is described as AUI and is an Anthropic metric. A baseline is 1.0 meaning a state would be using the amount of Claude we would expect, anything above means more than expected and vice versa. The distribution above is right skewed, with most states sitting below the 1.0 threshold and a few sitting far above 1.0. DC sits at 3.82 and Utah sits at 3.78 far above the rest of the states. 

| highest | index |
| --- | --- |
| DC | 3.82 |
| UT | 3.78 |
| CA | 2.13 |
| NY | 1.58 |
| VA | 1.57 |

| lowest | index |
| --- | --- |
| MS | 0.21 |
| WV | 0.23 |
| SD | 0.26 |
| AK | 0.31 |
| KY | 0.35 |

These values written above match those found in v3's report.


## Automation Share

![Automation_distribution](figures/exploratory_figures/automation_distribution.png)

This is the share of a state's classified collaboration that leans towards automation vs augmentation. The spread is much tighter than Adoption, many states are hovering around 50% with 2 distinct outliers:UT and SD .

| highest automation | share |
| --- | --- |
| UT | 73.4 |
| SD | 63.5 |
| ND | 56.0 |
| WY | 53.3 |

| highest augmentation | share |
| --- | --- |
| DC | 56.5 |
| VT | 56.4 |
| WA | 55.8 |
| NM | 55.0 |

Utah has the highest automation share 73.4%, with SD at 63.5%, this large percentage for Utah along with its abnormally high adoption rate makes it an interesting potential case study within the larger project. This is especially interesting when you consider DC which was the other large outlier in AUI has the highest augmentation share. V3's report flags Utah as possible automated traffic driven through that made it past their blockers so that is something to be aware of and it may be the reason its automation is so high, needs more substantiated evidence. 

| smallest samples | conversations |
| --- | --- |
| WY | 135 |
| AK | 139 |
| SD | 140 |
| ND | 183 | 

Above highlights that many of these state wide statistics need to be taken with a grain of salt since many states do not have a large sample to base off of, may highlight the need for a month long aggregation similar to the approach taken in release 6.


## Adoption against State GDP

![AUI vs GDP](figures/exploratory_figures/aui_vs_gdp.png)

GDP per working age capita is the only economic covariate already present in the initial download so provides some insight before joining the data externally. Across all states the correlation is 0.68 strong enough to show there is a relationship there.

As pointed out earlier we have 2 very strong AUI outliers in DC and Utah therefore the correlation without either state was considered. The correlation without DC is 0.42, and the correlation without Utah is 0.84 another indication that Utah is a very strong outlier.

## What is next based on the exploratory analysis 

Add in other economic/population data besides what currently resides such as occupation employment and wages, census industry mix etc. Research into Utah is this simply a coincidence based on one week of data is this a recurring thing across releases is there a reasonable explanation or is there something misleading happening. Handling sample sizes for small population and conversation states, a threshold of 100 conversation minimum is applied but breaking smaller states down to categories loses almost all information. Is 100 a reasonable minimum or should this be adjusted. 