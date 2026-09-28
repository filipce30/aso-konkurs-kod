#!/usr/bin/env bash
# Full pipeline: raw data -> results.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/clean/build_matrices.py
python3 scripts/clean/make_figures.py
Rscript analysis/mortality/fit_models.R
Rscript analysis/mortality/project_simulate.R
Rscript analysis/mortality/rh_refit.R
Rscript analysis/mortality/make_figures.R
python3 analysis/annuity/value_annuities.py
python3 analysis/system/01_extract_mapas_chart53.py
python3 analysis/system/02_system_liability.py
python3 analysis/system/03_member_choice.py
