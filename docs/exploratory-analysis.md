# Exploratory Analysis

This page collects the full converted Plotly set for the dataset organization work. These plots are descriptive. They document the available metadata, matched subset, missingness, and variable relationships used to decide what belongs in the public factsheet and what should not silently drive fold construction.

The page uses static previews first and loads the interactive Plotly version only when **Load Interactive Figure** is pressed. This prevents the browser from initializing dozens of Plotly charts at once.

## Main Insights

- The matched fold-design subset contains 203 origins from the 237 origin-level metadata rows currently present in the source metadata copy.
- Origin-level and patch-level class counts should be read separately because origins contribute different numbers of patches.
- The current patch-level matched subset is largest for OSCC, followed by leukoplakia with dysplasia and leukoplakia without dysplasia.
- Skin color, tobacco use, alcohol consumption, and sun exposure have high `Not informed` rates. They are useful for descriptive context, but they should not be treated as complete clinical covariates.
- Dysplasia severity is missing for many rows because it is not meaningful or available for every diagnostic category.
- Association charts are screening views. They describe relationships in the metadata and do not prove causality or downstream model quality.

## How To Read These Figures

- Count bars show how many origin or patch rows belong to each category.
- Percent labels are calculated within the plotted level.
- Row-percentage plots sum to 100 percent within each category on the x-axis.
- Column-percentage plots sum to 100 percent within each diagnosis.
- The colors use the Labcin blue/green palette with bright complementary colors for contrast.

## Diagnosis And Source Tasks

### Origin Diagnosis: Source Metadata vs Matched Subset

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/01a_origin_diagnosis_actual_vs_matched_stacked.html" data-plotly-title="Origin Diagnosis: Source Metadata vs Matched Subset">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/01a_origin_diagnosis_actual_vs_matched_stacked.png" alt="Origin Diagnosis: Source Metadata vs Matched Subset" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Compares all origin metadata rows with the currently matched origins used for fold design.</p>

### Origin Diagnosis In Matched Subset

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/01b_origin_diagnosis_matched_count_percent.html" data-plotly-title="Origin Diagnosis In Matched Subset">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/01b_origin_diagnosis_matched_count_percent.png" alt="Origin Diagnosis In Matched Subset" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Origin-level parent-image counts in the matched fold-design subset.</p>

### Patch Diagnosis In Matched Subset

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/01c_patch_diagnosis_matched_count_percent.html" data-plotly-title="Patch Diagnosis In Matched Subset">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/01c_patch_diagnosis_matched_count_percent.png" alt="Patch Diagnosis In Matched Subset" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Patch-row counts in the matched fold-design subset.</p>

### Patch Task II Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/02a_patch_taskii_count_percent.html" data-plotly-title="Patch Task II Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/02a_patch_taskii_count_percent.png" alt="Patch Task II Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for Task II across patch rows.</p>

### Origin Task II Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/02a_taskii_origin_count_percent.html" data-plotly-title="Origin Task II Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/02a_taskii_origin_count_percent.png" alt="Origin Task II Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for Task II across matched origins.</p>

### Patch Task II Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/02a_taskii_patch_count_percent.html" data-plotly-title="Patch Task II Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/02a_taskii_patch_count_percent.png" alt="Patch Task II Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for Task II across patch rows.</p>

### Patch Task III Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/02b_patch_taskiii_count_percent.html" data-plotly-title="Patch Task III Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/02b_patch_taskiii_count_percent.png" alt="Patch Task III Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for Task III across patch rows.</p>

### Origin Task III Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/02b_taskiii_origin_count_percent.html" data-plotly-title="Origin Task III Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/02b_taskiii_origin_count_percent.png" alt="Origin Task III Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for Task III across matched origins.</p>

### Patch Task III Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/02b_taskiii_patch_count_percent.html" data-plotly-title="Patch Task III Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/02b_taskiii_patch_count_percent.png" alt="Patch Task III Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for Task III across patch rows.</p>

### Patch Task IV Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/02c_patch_taskiv_count_percent.html" data-plotly-title="Patch Task IV Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/02c_patch_taskiv_count_percent.png" alt="Patch Task IV Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for Task IV across patch rows.</p>

### Origin Task IV Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/02c_taskiv_origin_count_percent.html" data-plotly-title="Origin Task IV Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/02c_taskiv_origin_count_percent.png" alt="Origin Task IV Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for Task IV across matched origins.</p>

### Patch Task IV Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/02c_taskiv_patch_count_percent.html" data-plotly-title="Patch Task IV Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/02c_taskiv_patch_count_percent.png" alt="Patch Task IV Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for Task IV across patch rows.</p>

## Demographic, Clinical, And Missingness Summaries

### Origin Age Group Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_origin_age_group_label_count_percent.html" data-plotly-title="Origin Age Group Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_origin_age_group_label_count_percent.png" alt="Origin Age Group Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for age group at origin level.</p>

### Origin Alcohol Consumption Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_origin_alcohol_consumption_count_percent.html" data-plotly-title="Origin Alcohol Consumption Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_origin_alcohol_consumption_count_percent.png" alt="Origin Alcohol Consumption Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for alcohol consumption at origin level.</p>

### Origin Dysplasia Severity Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_origin_dysplasia_severity_count_percent.html" data-plotly-title="Origin Dysplasia Severity Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_origin_dysplasia_severity_count_percent.png" alt="Origin Dysplasia Severity Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for dysplasia severity at origin level.</p>

### Origin Gender Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_origin_gender_count_percent.html" data-plotly-title="Origin Gender Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_origin_gender_count_percent.png" alt="Origin Gender Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for gender at origin level.</p>

### Origin Localization Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_origin_localization_count_percent.html" data-plotly-title="Origin Localization Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_origin_localization_count_percent.png" alt="Origin Localization Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for localization at origin level.</p>

### Origin Skin Color Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_origin_skin_color_count_percent.html" data-plotly-title="Origin Skin Color Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_origin_skin_color_count_percent.png" alt="Origin Skin Color Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for skin color at origin level.</p>

### Origin Sun Exposure Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_origin_sun_exposure_count_percent.html" data-plotly-title="Origin Sun Exposure Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_origin_sun_exposure_count_percent.png" alt="Origin Sun Exposure Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for sun exposure at origin level.</p>

### Origin Tobacco Use Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_origin_tobacco_use_count_percent.html" data-plotly-title="Origin Tobacco Use Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_origin_tobacco_use_count_percent.png" alt="Origin Tobacco Use Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for tobacco use at origin level.</p>

### Patch Age Group Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_patch_age_group_label_count_percent.html" data-plotly-title="Patch Age Group Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_patch_age_group_label_count_percent.png" alt="Patch Age Group Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for age group at patch level.</p>

### Patch Alcohol Consumption Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_patch_alcohol_consumption_count_percent.html" data-plotly-title="Patch Alcohol Consumption Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_patch_alcohol_consumption_count_percent.png" alt="Patch Alcohol Consumption Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for alcohol consumption at patch level.</p>

### Patch Dysplasia Severity Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_patch_dysplasia_severity_count_percent.html" data-plotly-title="Patch Dysplasia Severity Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_patch_dysplasia_severity_count_percent.png" alt="Patch Dysplasia Severity Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for dysplasia severity at patch level.</p>

### Patch Gender Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_patch_gender_count_percent.html" data-plotly-title="Patch Gender Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_patch_gender_count_percent.png" alt="Patch Gender Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for gender at patch level.</p>

### Patch Localization Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_patch_localization_count_percent.html" data-plotly-title="Patch Localization Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_patch_localization_count_percent.png" alt="Patch Localization Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for localization at patch level.</p>

### Patch Skin Color Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_patch_skin_color_count_percent.html" data-plotly-title="Patch Skin Color Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_patch_skin_color_count_percent.png" alt="Patch Skin Color Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for skin color at patch level.</p>

### Patch Sun Exposure Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_patch_sun_exposure_count_percent.html" data-plotly-title="Patch Sun Exposure Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_patch_sun_exposure_count_percent.png" alt="Patch Sun Exposure Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for sun exposure at patch level.</p>

### Patch Tobacco Use Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/03_patch_tobacco_use_count_percent.html" data-plotly-title="Patch Tobacco Use Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/03_patch_tobacco_use_count_percent.png" alt="Patch Tobacco Use Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Counts and percentages for tobacco use at patch level.</p>

### Origin Missing And Not-Informed Rates

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/04a_origin_missing_not_informed_rates.html" data-plotly-title="Origin Missing And Not-Informed Rates">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/04a_origin_missing_not_informed_rates.png" alt="Origin Missing And Not-Informed Rates" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows missing and `Not informed` percentages for origin-level metadata fields.</p>

### Patch Missing And Not-Informed Rates

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/04b_patch_missing_not_informed_rates.html" data-plotly-title="Patch Missing And Not-Informed Rates">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/04b_patch_missing_not_informed_rates.png" alt="Patch Missing And Not-Informed Rates" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Shows missing and `Not informed` percentages for patch-level metadata fields.</p>

## Age, Diagnosis, And Variable Associations

### Origin Age Group Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/05a_origin_age_group_count_percent.html" data-plotly-title="Origin Age Group Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/05a_origin_age_group_count_percent.png" alt="Origin Age Group Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Age-group counts and percentages used as context for diagnosis association views.</p>

### Patch Age Group Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/05a_patch_age_group_count_percent.html" data-plotly-title="Patch Age Group Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/05a_patch_age_group_count_percent.png" alt="Patch Age Group Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Age-group counts and percentages used as context for diagnosis association views.</p>

### Origin Age Group Distribution For Diagnosis Review

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/05b_origin_age_group_count_percent.html" data-plotly-title="Origin Age Group Distribution For Diagnosis Review">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/05b_origin_age_group_count_percent.png" alt="Origin Age Group Distribution For Diagnosis Review" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Age-group counts and percentages used as context for diagnosis association views.</p>

### Patch Age Group Distribution For Diagnosis Review

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/05b_patch_age_group_count_percent.html" data-plotly-title="Patch Age Group Distribution For Diagnosis Review">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/05b_patch_age_group_count_percent.png" alt="Patch Age Group Distribution For Diagnosis Review" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Age-group counts and percentages used as context for diagnosis association views.</p>

### Origin Diagnosis By Age Group: Row Percentages

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/06_diagnosis_by_age_group_row_percent.html" data-plotly-title="Origin Diagnosis By Age Group: Row Percentages">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/06_diagnosis_by_age_group_row_percent.png" alt="Origin Diagnosis By Age Group: Row Percentages" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one age group.</p>

### Patch Diagnosis By Age Group: Row Percentages

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/06a_diagnosis_by_age_group_row_percent.html" data-plotly-title="Patch Diagnosis By Age Group: Row Percentages">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/06a_diagnosis_by_age_group_row_percent.png" alt="Patch Diagnosis By Age Group: Row Percentages" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one age group.</p>

### Diagnosis By Age Group: Column Percentages

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/06b_diagnosis_by_age_group_column_percent.html" data-plotly-title="Diagnosis By Age Group: Column Percentages">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/06b_diagnosis_by_age_group_column_percent.png" alt="Diagnosis By Age Group: Column Percentages" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one diagnosis.</p>

### Origin Diagnosis By Alcohol Consumption

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/07_origin_diagnosis_by_alcohol_consumption_row_percent.html" data-plotly-title="Origin Diagnosis By Alcohol Consumption">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/07_origin_diagnosis_by_alcohol_consumption_row_percent.png" alt="Origin Diagnosis By Alcohol Consumption" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one alcohol consumption category.</p>

### Origin Diagnosis By Gender

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/07_origin_diagnosis_by_gender_row_percent.html" data-plotly-title="Origin Diagnosis By Gender">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/07_origin_diagnosis_by_gender_row_percent.png" alt="Origin Diagnosis By Gender" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one gender category.</p>

### Origin Diagnosis By Localization

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/07_origin_diagnosis_by_localization_row_percent.html" data-plotly-title="Origin Diagnosis By Localization">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/07_origin_diagnosis_by_localization_row_percent.png" alt="Origin Diagnosis By Localization" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one localization category.</p>

### Origin Diagnosis By Skin Color

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/07_origin_diagnosis_by_skin_color_row_percent.html" data-plotly-title="Origin Diagnosis By Skin Color">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/07_origin_diagnosis_by_skin_color_row_percent.png" alt="Origin Diagnosis By Skin Color" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one skin color category.</p>

### Origin Diagnosis By Sun Exposure

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/07_origin_diagnosis_by_sun_exposure_row_percent.html" data-plotly-title="Origin Diagnosis By Sun Exposure">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/07_origin_diagnosis_by_sun_exposure_row_percent.png" alt="Origin Diagnosis By Sun Exposure" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one sun exposure category.</p>

### Origin Diagnosis By Tobacco Use

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/07_origin_diagnosis_by_tobacco_use_row_percent.html" data-plotly-title="Origin Diagnosis By Tobacco Use">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/07_origin_diagnosis_by_tobacco_use_row_percent.png" alt="Origin Diagnosis By Tobacco Use" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one tobacco use category.</p>

### Patch Diagnosis By Alcohol Consumption

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/07_patch_diagnosis_by_alcohol_consumption_row_percent.html" data-plotly-title="Patch Diagnosis By Alcohol Consumption">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/07_patch_diagnosis_by_alcohol_consumption_row_percent.png" alt="Patch Diagnosis By Alcohol Consumption" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one alcohol consumption category.</p>

### Patch Diagnosis By Gender

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/07_patch_diagnosis_by_gender_row_percent.html" data-plotly-title="Patch Diagnosis By Gender">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/07_patch_diagnosis_by_gender_row_percent.png" alt="Patch Diagnosis By Gender" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one gender category.</p>

### Patch Diagnosis By Localization

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/07_patch_diagnosis_by_localization_row_percent.html" data-plotly-title="Patch Diagnosis By Localization">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/07_patch_diagnosis_by_localization_row_percent.png" alt="Patch Diagnosis By Localization" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one localization category.</p>

### Patch Diagnosis By Skin Color

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/07_patch_diagnosis_by_skin_color_row_percent.html" data-plotly-title="Patch Diagnosis By Skin Color">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/07_patch_diagnosis_by_skin_color_row_percent.png" alt="Patch Diagnosis By Skin Color" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one skin color category.</p>

### Patch Diagnosis By Sun Exposure

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/07_patch_diagnosis_by_sun_exposure_row_percent.html" data-plotly-title="Patch Diagnosis By Sun Exposure">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/07_patch_diagnosis_by_sun_exposure_row_percent.png" alt="Patch Diagnosis By Sun Exposure" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one sun exposure category.</p>

### Patch Diagnosis By Tobacco Use

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/07_patch_diagnosis_by_tobacco_use_row_percent.html" data-plotly-title="Patch Diagnosis By Tobacco Use">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/07_patch_diagnosis_by_tobacco_use_row_percent.png" alt="Patch Diagnosis By Tobacco Use" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Each bar sums to 100 percent within one tobacco use category.</p>

### Categorical Variable Association By Cramer's V

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/08_categorical_association_cramers_v.html" data-plotly-title="Categorical Variable Association By Cramer&#x27;s V">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/08_categorical_association_cramers_v.png" alt="Categorical Variable Association By Cramer&#x27;s V" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Full descriptive association list. Higher values indicate stronger categorical association, not causality.</p>

## Lesion Size

### Lesion Size Distribution

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/09_larger_size_histogram_count_percent.html" data-plotly-title="Lesion Size Distribution">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/09_larger_size_histogram_count_percent.png" alt="Lesion Size Distribution" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Histogram of the larger-size metadata field across patch rows.</p>

### Lesion Size By Diagnosis

<div class="plotly-lazy-card" data-plotly-src="../visualizations/generated/10_lesion_size_by_diagnosis.html" data-plotly-title="Lesion Size By Diagnosis">
  <img class="plotly-preview-image" src="../assets/generated/plotly_previews/10_lesion_size_by_diagnosis.png" alt="Lesion Size By Diagnosis" loading="lazy">
  <button type="button" class="plotly-load-button">Load Interactive Figure</button>
  <div class="plotly-lazy-target"></div>
</div>

<p class="figure-caption">Descriptive lesion-size spread by diagnosis. This is not a fold-selection rule.</p>

<div class="ndb-next" markdown>
<strong>Next read:</strong> [Dataset Factsheet](factsheet.md)
</div>
