# Gap statement

Domestic literature on stochastic mortality modelling for North Macedonia is essentially
non-existent: no peer-reviewed or working paper applying a Lee-Carter-family or CBD-family
model to Macedonian data was found after searching Macedonian- and English-language academic
databases, UKIM/MANU repositories, and the Economic Institute - Skopje's publication list. The
single close domestic precedent is Bajatov (2015), an ASO award-winning paper that corrects a
*static* Macedonian population table for annuitant anti-selection using imported foreign select
margins - a cross-sectional adjustment, not a time-dynamic projection. Domestic pension-system
literature is thinner still: two recent items (Xhemali, Bexheti & Pulejkov 2025; Petreski &
Gacov 2018) model first/second-pillar fiscal sustainability but do not touch mortality
assumptions, capital requirements, or the payout/annuity phase at all. No Macedonian source
was found that (a) fits a stochastic mortality model with quantified projection uncertainty to
Macedonian data, (b) prices a cohort-projected annuity factor against a static one, or (c) tests
the Solvency II standard longevity shock against a model-based VaR for Macedonian annuitants.
Regionally, Croatia, Kosovo, Serbia, Bulgaria and Slovenia each have recent (2019-2026) payout-
phase or decumulation-policy literature, but none apply a stochastic mortality model either -
the region's second-pillar literature is policy/fiscal, not actuarial. This thinness is itself
the finding: it is the evidentiary gap this paper fills, not a search failure (search log:
Macedonian and English queries across ДЗС/MAKSTAT, MANU, UKIM Economic Faculty and Economic
Institute repositories, ASO award archive, Google Scholar-indexed sources via web search, and
Crossref bibliographic search on ~50 targeted query strings, including МАПАС/АСО/НБРСМ archives,
World Bank/OECD/ESPN and Croatian/Slovenian/Serbian actuarial and academic sources, 2026-09-22).

Two primary sources make the picture concrete: (i) МАПАС's own 2024 annual report
(`mapas2025izvestaj`) shows zero life annuities paid from the second pillar as of end-2024 (all
71 ongoing old-age payouts are programmed withdrawals), independently corroborated by the same
absence of any second-pillar annuity business in АСО's 2025 insurance-market report
(`aso2026godishen`) - the paper's readiness framing (a market that has not yet paid a
second-pillar annuity) is therefore a documented fact, not a hypothesis; (ii) the State
Statistical Office's own population projections to 2070 (`sso2023projections`) use two
deterministic (not stochastic) mortality hypotheses and explicitly abstract away the COVID-19
mortality shock rather than modelling it - direct primary-source evidence that no Macedonian
institution, public or academic, currently publishes a stochastic mortality projection with
quantified uncertainty. No Western Balkan / CEE academic source applying a Lee-Carter/CBD-family
model to any regional country's data was found.

## Novelty claims

1. **First stochastic (cohort-projected) mortality model for North Macedonia with quantified
   uncertainty.** No domestic source fits an LC/CBD/RH-family model to MK data; the only
   domestic mortality-adjustment work (Bajatov 2015) is a static cross-sectional correction, not
   a projection. Evidence: absence established by targeted search (see gap statement above);
   contrast documented in notes.md under `bajatov2015analiza`. `sso2023projections` (the State
   Statistical Office's own 2070 population projections) shows that even the national
   statistical authority uses deterministic expert-judgement mortality hypotheses with no
   quantified uncertainty band, and explicitly sets aside COVID-19 rather than modelling it -
   the gap is documented at the source, not just inferred from absence.

2. **First test of the Solvency II standard longevity shock against a model-based 99.5% VaR
   using Macedonian data.** Börger (2010) - calibrated on **England and Wales male mortality**
   (HMD 1947-2006), analysing the **25% QIS4** shock - Plat (2011), Richards, Currie & Ritchie
   (2014), Jarner & Møller (2015), Boonen (2017) and Olivieri & Pitacco (2009) supply the method,
   but all are applied to English/UK/Danish/Italian or other West-European data; no regional
   (Western Balkan/CEE) application of this comparison was found. The shock's own calibration
   documentation, `eiopa2014underlying` (EIOPA-14-322), shows that the 5-35% (avg. ~18%) figure
   came from a **Watson Wyatt** (2004) study; Towers Perrin is the source for the
   *stochastic-model methodology* used in a separate 9-country historical/stochastic calibration
   exercise (mortality.org data). **The 9 countries are not named in the EIOPA document** - the
   statement that none is in the Western Balkans is this paper's own inference, not something the
   source states, and is worded as an inference. Evidence: `borger2010deterministic`,
   `plat2011oneyear`, `richards2014value`, `jarner2015partial`, `boonen2017solvency`,
   `olivieripitacco2009stochastic`, `eiopa2014underlying` in refs.bib - all non-Balkan in their
   own right (Börger/E&W, Plat/Netherlands, Richards et al./UK, Jarner & Møller/Denmark,
   Boonen/general EU, Olivieri & Pitacco/general); no counter-example located despite dedicated
   search queries on CEE stochastic mortality applications.

3. **First quantification of static-vs-cohort annuity mispricing and system-level second-pillar
   liability for North Macedonia, at a moment when the region is actively deciding this
   question.** Šterpin, Laporšek & Vovk (2026) show large welfare costs from restrictive
   decumulation design in Slovenia; Milev (2020) shows Bulgaria facing the same design choice
   contemporaneously. No equivalent quantification exists for MK, where no insurer has yet paid
   out a second-pillar life annuity (`mapas2025izvestaj`, МАПАС's own 2024 report, Table 5.12:
   all 71 ongoing old-age payouts are programmed withdrawals; corroborated independently by
   `aso2026godishen`, АСО's 2025 market report, which records no second-pillar annuity business
   at all). This makes the paper a *readiness* study, answering the question the market has not
   yet had to answer for itself. Evidence: `sterpin2026policy`, `milev2020payout`,
   `vittas2010designing`, `jamesvittas2000decumulation` (region-wide framing),
   `mapas2025izvestaj`, `aso2026godishen` (MK-specific evidence of zero second-pillar annuities
   paid to date). The *licensing* basis of the readiness framing (no insurer holds insurance
   class 24, the second-pillar-annuity class) is a separate claim from the zero-payouts fact
   above and is anchored to `aso2026registar` (ASO's life-insurer register), not to
   `mapas2025izvestaj`/`aso2026godishen`, which say nothing about licensing classes.

## Bajatov (2015) - scope relative to the novelty claims

The full text of Bajatov (2015) contains **no mortality projection, no cohort table, no
Lee-Carter (or any other stochastic mortality) model, and no VaR calculation** of any kind. It is
purely a static, cross-sectional correction of a single Macedonian population table for
annuitant-selection margins, built from imported (US/UK/Swiss) select mortality, as described in
the `bajatov2015analiza` entry of notes.md. None of the three novelty claims is therefore
affected: claim 1 (no domestic stochastic/cohort projection exists) holds, since Bajatov never
attempted one; claim 2 (no domestic Solvency-II VaR-vs-shock test exists) holds, since Bajatov
never computed a VaR; claim 3 (no domestic static-vs-cohort mispricing/system-liability
quantification exists) holds, since Bajatov's correction is static-only and has no cohort
comparator and no system-level liability figure.
