# Literature notes

Reading notes on the sources used in this paper, organised by topic. Each entry gives the
source's question, method, key finding and relevance to this paper. BibTeX keys match `refs.bib`.

## Stochastic mortality models

**lee1992modeling** - Lee & Carter (1992). Question: how to forecast a whole age schedule of US
mortality with one time-varying index. Method: SVD of log central death rates into age effect
a_x, age-time bilinear term b_x*k_t, fit k_t as ARIMA/random walk with drift. Finding: a simple
2-parameter-per-age model captures most of the historical decline and gives credible intervals
derived analytically from the closed-form forecast variance of the ARIMA(0,1,0)/random-walk-
with-drift model for k_t, not via Monte Carlo simulation - simulation-based prediction intervals
(bootstrap/Monte Carlo) are a later development (see brouhns2002poisson and the bootstrap
approach used in this project). Relevance: foundation model for the mortality-projection
methodology; a likely baseline given the short domestic data history.

**brouhns2002poisson** - Brouhns, Denuit & Vermunt (2002). Question: how to give Lee-Carter a
proper likelihood instead of SVD-on-logs plus ad hoc re-estimation of k_t. Method: Poisson
log-bilinear regression fit by Newton-Raphson, deaths ~ Poisson(exposure * exp(a_x+b_x k_t)).
Finding: matches classic Lee-Carter closely but gives a coherent likelihood for weighting,
missing cells and bootstrap. Relevance: this is the estimation method underlying StMoMo's `lc()`
fitter, and the fallback recipe if R/StMoMo estimation is unavailable.

**cairns2006two** - Cairns, Blake & Dowd (2006), CBD model. Question: can a simpler, two-factor
model of the logit of q_x fit old-age (60+) mortality as well as Lee-Carter, with more
transparent parameter uncertainty. Method: logit(q_xt) = k1_t + k2_t*(x - x̄); random walk with
drift on (k1,k2), MCMC/bootstrap for uncertainty; calibrated on England & Wales males,
1961-2002. Finding: fits old-age mortality curves well without an age-response function that
needs separate smoothing, over the 60-90 age range (the primary source states "the mid-point of
our age 60-90 data sets," not 60-89). Used widely for annuity/pension pricing at exactly the
ages this paper needs. Relevance: core candidate model for the mortality-projection stage (the
CBD M5 variant).

**renshaw2006cohort** - Renshaw & Haberman (2006), RH model. Question: does adding a cohort
(year-of-birth) effect to Lee-Carter materially improve fit where cohort effects are visible
(e.g. the UK "golden cohort"). Method: adds a third bilinear term b_x^(2) * gamma_(t-x) to
Lee-Carter. Finding: better fit where cohort effects exist, but convergence and identifiability
are harder (documented in Cairns et al. 2009). Relevance: motivates including RH only if it
converges stably in the model-selection stage - this paper is both the justification and the
warning.

**cairns2009quantitative** - Cairns et al. (2009). Question: which of 8 stochastic mortality
models is preferable, judged on fit, parameter parsimony and robustness. Method: applies
Lee-Carter, RH, the CBD family (M5-M7), APC and others to England & Wales and US data;
backtesting. Finding: no single model dominates; CBD-cohort variants do best for higher ages in
England & Wales, RH for US males. Their clearly stated selection criteria are BIC/parsimony and
parameter-estimate/forecasting robustness; "biological reasonableness"/"plausibility" is not
confirmed as their own explicit term (the paper's full enumerated criteria list sits behind a
paywall) and should not be attributed to them as a named criterion. Relevance: template for the
model-selection section (BIC + backtest).

**villegas2018stmomo** - Villegas, Kaishev & Millossovich (2018), StMoMo package paper,
pp.1-38. Question/method: unifies Lee-Carter, the CBD family, RH, APC etc. under one GNM-based
estimation and bootstrap/simulation framework in R. The package covers the vast majority of
stochastic mortality projection models, not literally all of them - SAINT (jarner2011saint) and
the Bayesian specifications (wong2023bayesian, miyata2022extending) discussed elsewhere in this
review are not implemented in StMoMo. Relevance: this is the software actually used for the
projection stage; cite for methodology and to justify software choice/reproducibility.

**thatcher1998force** - Thatcher, Kannisto & Vaupel (1998), monograph. Question: which
parametric law best describes mortality at 80-120 given 13 countries' data. Method: fits ages
80-98 by binomial maximum likelihood, per available secondary description of the monograph (the
original 1998 text was not directly reopened to confirm this specific detail). Finding: the
logistic model and its Kannisto approximation fit best; mortality deceleration (not pure
exponential increase) appears at the oldest ages. This project's own old-age closure (Poisson
likelihood, ages 80-99) should be cited to wilmoth2025methods (HMD Methods Protocol v6, p.37:
"Assuming that Dx ∼ Poisson(Ex μx+0.5(a,b))," fit to ages 80 and above), not to Thatcher et al.,
which is the source for the Kannisto/logistic functional form only. Relevance: justifies the
Kannisto closure at the oldest ages given thin old-age data, with the estimator itself cited to
wilmoth2025methods.

**wilmoth2025methods** - Wilmoth, Andreev, Jdanov, Glei & Riffe (2025), Human Mortality Database
Methods Protocol, Version 6. Question: none (technical protocol). Content: canonical method for
constructing exposure-to-risk, death rates and life tables from raw population/vital-registration
data, including the Poisson old-age closure fit to ages 80 and above. Relevance: the standard
against which the treatment of the 2021-census-driven revision of the domestic 2002-2021
population/exposure series is benchmarked; cite when justifying the exposure-construction
method and the old-age closure estimator.

**currie2016glm** - Currie (2016). Question: how to fit generalized linear/non-linear (GLM/GNM)
mortality models, including APC structures and their identifiability constraints. Relevance: the
estimation-framework reference underlying StMoMo's GNM fitters; pairs with
hunt2020identifiability on the RH/APC convergence caveat.

**hunt2020identifiability** - Hunt & Blake (2020), *Annals of Actuarial Science* 14(2),
pp.500-536, "Identifiability in Age/Period/Cohort Mortality Models" (DOI
10.1017/S1748499520000123). This is the age/period/**cohort** companion paper, distinct from the
companion age/period-only article (pp.461-499, DOI 10.1017/S1748499520000111), which does not
discuss cohort identifiability at all; the citations in this project concern the cohort term
specifically (the RH/APC convergence caveat), so this is the correct paper for that purpose.
Question: how to resolve identifiability (non-uniqueness) specifically where cohort parameters
are added to age/period mortality models. Relevance: direct methodological warning underpinning
the "RH only if it converges stably" caveat - cite when explaining why a chosen identification
scheme was necessary, not arbitrary.

**dowd2010backtesting** - Dowd, Cairns, Blake, Coughlan, Epstein & Khalaf-Allah (2010). Question:
how to backtest a stochastic mortality model's density forecasts (not just point forecasts) ex
post. Relevance: template for the backtest step - particularly important given the domestic
series' short calibration window, where a single point-forecast comparison would be weak
evidence.

**leemiller2001evaluating** - Lee & Miller (2001). Question: how well did the original 1992
Lee-Carter US forecasts actually perform once the future arrived. Finding: identifies systematic
patterns in over/under-projection. Relevance: sets realistic expectations for how much confidence
to place in a Lee-Carter-style fit to a much shorter domestic series - direct input to the
paper's limitations section.

**booth2008mortality** - Booth & Tickle (2008). Question: comprehensive review of mortality
modelling/forecasting methods (extrapolative, explanatory, structural). Relevance:
literature-review backbone for the model-selection section, complementing
cairns2009quantitative's empirical comparison with a methods taxonomy.

## Small-population and coherent methods

**li2005coherent** - Li & Lee (2005). Question: how to forecast mortality for a population
without letting its long-run trend diverge implausibly from a related, longer-history
population. Method: augmented common-factor Lee-Carter: a shared long-run B_x*K_t plus
population-specific short-run deviations k(t,i), modelled either as a random walk (RW) or as
AR(1). Finding: coherent forecasts avoid the "explosive divergence" failure mode of independent
Lee-Carter fits on short series - but in their own worked example (Sweden male/female, and
repeated for their wider country panels), Li & Lee's own explanation-ratio test rejects AR(1)
for both sexes: the AR(1) explanation ratio for k(t,i) (.880 male / .876 female) is lower than
the plain common-factor-model ratio (.883 / .895), so introducing an AR(1) population-specific
factor would make the fit worse, not better. This is evidence that AR(1) is not a safe default
for k(t,i) - it needs testing per population, not assuming. Relevance: a robustness option if the
domestic series is judged too short/noisy on its own - could borrow an international/Balkan
common trend as an anchor; relevant to a limitations-and-extensions discussion even if not the
main model.

**jarner2011saint** - Jarner & Kryger (2011), the SAINT model. Question: how to get biologically
plausible, stable long-run mortality projections for a small population without borrowing so
much from a reference population that local signal is lost. Method: frailty surface fitted on a
large reference population, small-population deviations modelled as a time series. Finding: used
in production by the Danish ATP pension fund for over a decade. Relevance: the closest
methodological analogue to this paper's core problem (a small population needing plausible
projections) - discussed prominently in the methodology section as a named alternative/
robustness check to Lee-Carter/CBD, alongside li2005coherent and hyndman2013coherent as ways of
borrowing strength from larger populations.

**hyndman2013coherent** - Hyndman, Booth & Yasmeen (2013). Question: functional-data alternative
to Li & Lee (2005) for coherent multi-population forecasting. Method: product-ratio
decomposition of functional time series. Relevance: second concrete option (with li2005coherent)
for anchoring the domestic series to a reference population if it proves too short/noisy - part
of the limitations/robustness discussion.

**miyata2022extending** - VAE + Bayesian extension of Lee-Carter (2022). Relevance: one paragraph
in the literature review on ML/Bayesian mortality forecasting as a stated future-work direction;
not used as a candidate model given the short domestic series (a data-hungry method).

**wong2023bayesian** - Fully Bayesian APCI model with informative priors (2023), explicitly built
for shorter/noisier series. Relevance: the strongest "recent Bayesian" citation for a short-series
country, worth a sentence in limitations/future work on Bayesian shrinkage as an alternative to
the bootstrap approach used here.

## COVID-19 handling

**dang2026impact** - COVID-19 mortality impact across 34 countries/economies (2026), stochastic
model with adjustable pandemic-shock decay. Relevance: direct support for the three
COVID-handling variants considered in the projection stage; cite when justifying why 2020-21
needs special treatment rather than being dropped or ignored.

**schnurch2022impact** - Schnürch, Kleinow, Korn & Wagner (2022). Question: how much does
including 2020 in a mortality-model calibration window distort annuity/insurance valuation.
Method: nine-European-country Lee-Carter comparison across inclusion/exclusion/adjustment
variants. Finding: including 2020 can move annuity values by up to 9% and sharply inflates
prediction uncertainty even after mortality normalises. Relevance: primary methodological
reference for the three COVID-handling variants, alongside dang2026impact.

**robben2022assessing** - Robben, Antonio & Devriendt (2022). Question: how to extend a
multi-population stochastic model with an explicit COVID-shock component rather than simply
dropping or including 2020-21 as normal data. Relevance: second concrete COVID-handling method
option, and specifically relevant if the domestic series ends up modelled jointly with a
reference population (li2005coherent/hyndman2013coherent) rather than standalone.

## Longevity capital and Solvency II

**borger2010deterministic** - Börger (2010). Question: how does the Solvency II QIS4 25%
standard longevity shock compare to a model-based 99.5% VaR. Method: compares the deterministic
shock against stochastic VaR from a mortality model fitted to the male general population of
England and Wales, HMD deaths/exposures 1947-2006. The shock analysed is 25% (the pre-2010 QIS4
calibration Börger is critiquing), not 20% (the current Art. 138 figure, see eu2015delegated) -
the paper keeps using 25% because it focuses on the shock's structure, not its exact level.
Finding: the standard shock is not uniformly conservative - it can under- or overstate the
model-based capital need depending on age and portfolio. Relevance: direct methodological
template for the capital-adequacy question; expect an analogous, data-dependent (not assumed)
direction of bias domestically, against the correctly described 20% Art.138 comparator rather
than Börger's own 25%.

**plat2011oneyear** - Plat (2011). Question: how to compute a one-year (not run-off) VaR for
longevity/mortality risk, consistent with Solvency II's one-year horizon. Method: decomposes
risk into level/trend/volatility components with a recalibration step. Relevance: alternative to
the full run-off VaR used as the main approach; a stretch-goal method alongside Richards et al.
(2014).

**richards2014value** - Richards, Currie & Ritchie (2014). Question: practical one-year VaR
framework for longevity trend risk usable by practitioners. Method: applies a P-spline/CMI-style
projection with a one-year re-estimation VaR. Relevance: the stretch-goal method for a one-year
VaR, alongside plat2011oneyear.

**eu2009solvency / eu2015delegated** - Solvency II Level 1 Directive and Level 2 Delegated
Regulation. Relevance: eu2015delegated Art. 138 is the literal legal text of the −20% standard
shock used as the capital-adequacy comparator; eu2009solvency is the parent directive
establishing the standard-formula/VaR 99.5% framework that the domestic supervisory mandate
implicitly echoes.

**jarner2015partial** - Jarner & Møller (2015). Question: how to build a partial internal model
for longevity risk consistent with the Solvency II one-year 99.5% VaR standard. Relevance: core
method reference alongside borger2010deterministic, plat2011oneyear and richards2014value for the
capital-adequacy section.

**boonen2017solvency** - Boonen (2017). Question: what does the Solvency II SCR look like if
built on expected shortfall instead of VaR. Relevance: a robustness citation questioning whether
99.5% VaR (the main comparator) is itself the right risk measure - useful for the
discussion/limitations section.

**olivieripitacco2009stochastic** - Olivieri & Pitacco (2009). Question: how much does
target/solvency capital change under a stochastic (projected) mortality model versus a
deterministic one. Relevance: methodological bridge between the paper's projection work and its
capital-adequacy question; predates and complements borger2010deterministic.

**eiopa2014underlying** - EIOPA (2014), EIOPA-14-322, "The Underlying Assumptions in the Standard
Formula for the SCR Calculation." Question: none (regulatory calibration documentation). Finding:
this is the origin documentation of the Solvency II 20% longevity shock. The 5-35% (avg. ~18%)
uniform-decrease figure behind that calibration is from a Watson Wyatt (2004) study, not Towers
Perrin. Internal-model feedback separately indicated a median stress of 25%. A separate 9-country
historical/stochastic calibration exercise (mortality.org data, unisex improvements 1992-2006)
found historical improvements exceeding 25% for most ages, while a stochastic model of future
improvements implied a lower stress; a footnote there says that stochastic model "was similar to
the stochastic model presented by Towers Perrin to the UNESPA" (21 Jan 2009) - so Towers Perrin is
the source for the stochastic-model methodology in the 9-country exercise, not for the 5-35%/18%
figure. The nine countries are not named in the source (only "data is available at
www.mortality.org" in a footnote); any statement that none of the nine is a Western Balkan
country is this paper's own inference from likely HMD membership at the time, not a fact stated
in the EIOPA document, and should be worded accordingly ("presumably," "the countries are not
named, but..."). Relevance: essential primary source for the capital-adequacy question - shows
the "20%" was itself calibrated on Western European data, which is the direct evidentiary hook
for asking whether it transfers to the domestic setting.

**ec2025delegated** - The October 2025 EU delegated regulation text (cost-of-capital 6%->4.75%),
companion to eu2015delegated. Relevance: current cost-of-capital calibration for the
capital-adequacy section.

## Annuity economics

**mitchell1999new** - Mitchell, Poterba, Warshawsky & Brown (1999). Question: what is the
"money's worth" (expected present value of payments / premium) of individual annuities in the
US, and how much of any shortfall is adverse selection vs. loads. Method: compares annuity
prices against population and annuitant mortality tables and market discount rates. Relevance:
the classic money's-worth methodology; useful for framing the static-vs-cohort-table cost
question even though there is no live retail annuity market domestically yet to benchmark
against.

**blake2006living** - Blake, Cairns & Dowd (2006), "Living with Mortality." Question: survey of
longevity risk transfer instruments (longevity bonds, swaps) and why markets for them are slow
to develop. Relevance: background for discussing whether a small second-pillar system could ever
access such instruments (almost certainly not soon) - supports a buy-and-hold reserving framing
over risk-transfer.

**blake2023longevity** - "Longevity Risk and Capital Markets" 2021-22 annual update. Relevance:
evidence that even large annuity markets struggle to transfer longevity risk to capital markets -
a fortiori true domestically; supports the discussion of why domestic reserving/regulation (not
risk transfer) is the near-term policy lever.

**yaari1965uncertain** - Yaari (1965). Question: what is the utility-maximising
consumption/annuitisation choice under lifetime uncertainty. Finding: with actuarially fair
annuities and no bequest motive, full annuitisation is optimal. Relevance: the foundational
theoretical benchmark for the take-up-rate discussion - the yardstick against which the domestic
near-total absence of an annuity market should be read.

**brown2001private** - Brown (2001). Question: how much do bequest motives and pre-existing
annuitisation (e.g. a PAYG first pillar) reduce the utility gain from voluntary annuitisation
relative to the Yaari (1965) full-annuitisation ideal. Relevance: nuances the take-up-rate
scenarios (30/60/100%) - real-world take-up is never 100% even where annuities are available and
priced fairly, so 100% should be read as an upper-bound stress scenario, not a forecast.

**jamesvittas2000decumulation** - James & Vittas (2000), World Bank Policy Research Working Paper
2464. Question: what payout-phase policy menu (mandatory/voluntary annuitisation, programmed
withdrawal, lump sum) suits countries transitioning to funded DC pillars. Relevance: pre-dates
and frames rocha2010designing/vittas2010designing; shows the domestic payout-phase design
question is a 25-year-old, still-unresolved debate in the World Bank's own client countries, not
a novel problem.

**finkelsteinpoterba2004adverse** - Finkelstein & Poterba (2004). Question: do annuitants who
select non-standard contract features have systematically different mortality from the rest of
the pool. Finding: yes - direct empirical evidence for adverse selection in a real (UK) annuity
market. Relevance: the classic adverse-selection companion to mitchell1999new's money's-worth
methodology; also the mechanism that motivates Bajatov (2015)'s annuitant-mortality correction
and this paper's cohort-vs-static comparison.

**milevsky2006calculus** - Milevsky (2006), *The Calculus of Retirement Income* (Cambridge
University Press). Question/method: textbook-level financial modelling of pension annuities and
life insurance, including optimal-annuitisation-timing arguments. Relevance: standard
reference-book citation for the annuity-pricing methodology section, alongside the journal
literature.

## Domestic and regional pension literature

**bajatov2015analiza** - Bajatov (2015), ASO award winner. Question: how much lower is annuitant
mortality than general-population mortality domestically, using imported select mortality
margins (US/UK/Switzerland) applied to correct population tables. Method: builds a "margin"
between annuitant and population q_x from foreign annuitant experience, applies it to the latest
population table, recomputes commutation functions. Finding: annuitant mortality is materially
lower than population mortality at nearly all ages (negative margin), narrowing with age. This is
the direct domestic precedent for the present paper and is explicitly differentiated from it:
Bajatov corrects a static table for selection; this paper instead builds a stochastic,
time-projected (cohort) table and asks a capital-adequacy question that Bajatov does not address
at all. Bajatov (2015) contains no mortality projection, no cohort table, no Lee-Carter (or any
stochastic mortality) model, and no VaR calculation - it is a static cross-sectional correction of
a population table for annuitant selection only, and this paper's three novelty/primacy claims
rest on that reading.

**srbinoski2019life** - Srbinoski (2019), ASO award winner. Question: does financial development
raise or lower life-insurance demand once borrowing constraints are modelled (cross-country
panel, not domestic-specific). Finding: more credit-constrained countries have higher
life-insurance penetration on average. Relevance: background only, for the economy/
insurance-sector-development section; not usable for the mortality/annuity questions.

**xhemali2025fiscal** - Xhemali, Bexheti & Pulejkov (2025). Question: is the second-pillar-
adjacent fiscal position of the domestic pension fund sustainable. Method: reviews contribution
splits, investment performance and indexation practice (verified at abstract/metadata level;
full text paywalled). Relevance: most recent domestic academic source on second-pillar fiscal
sustainability; cite for system-level framing, noting only metadata was checked.

**petreski2018sustainability** - Petreski & Gacov (2018), Finance Think Policy Study 14.
Question: is the PAYG-dominant domestic pension system fiscally sustainable, and what do
parametric/structural reform scenarios do to the deficit. Method: MK-PENS dynamic
microsimulation model calibrated on the 2017 Quality of Life Survey and PDIF administrative
aggregates. Finding: the deficit is structural and demographically driven; several reform
scenarios modelled (retirement age, contribution rate, indexation). Relevance: best available
domestic quantitative model of first-pillar finances - background/cross-check for take-up
scenarios and the economy section; predates the 2021 census revision.

**petreski2021dynamic** - Petreski & Petreski (2021), *Journal of Pension Economics & Finance*
20(1). Question: the same MK-PENS dynamic microsimulation question as
petreski2018sustainability, peer-reviewed. Finding: the deficit is structural/demographic;
combined reform scenarios (retirement age + contribution rate + indexation) work best.
Relevance: the strongest domestic peer-reviewed (not grey-literature) source for the economy
section and for first-pillar framing; cited alongside, not instead of, petreski2018sustainability.

**lozanoska2024demografski** - Lozanoska & Janeska, eds. (2024), Economic Institute - Skopje.
Question: what changed in the domestic population structure between 2002 and 2021, post-census.
Finding: depopulation in 66/80 municipalities since 2002, accelerating demographic aging,
emigration as the dominant driver (not fertility/mortality alone). Relevance: the only
book-length domestic academic treatment of the post-2021-census demographic picture found;
supports the census-bias discussion and is a citable domestic source for demographic-aging
claims.

**iops2020northmacedonia** - IOPS Country Profile: North Macedonia (Dec 2020). Factual/
institutional, not academic. Confirms retirement ages 64 (M)/62 (F), min. 15 years' service, and
the 12.8%/6% PAYG/funded split. Relevance: independent (non-MAPAS) cross-check of retirement
ages, corroborating the primary-law reading rather than replacing it.

**mapas2025izvestaj** - МАПАС (2025), annual report on the state of funded pension insurance,
covering 2024. Question: none (statistical/regulatory report). Method: administrative data
compiled by the pension supervisor. Finding: zero life annuities were paid out from the second
pillar in 2024 - all 71 ongoing old-age payouts (35 new in 2024) were programmed withdrawals
(Table 5.12); confirms retirement ages 64(M)/62(F), min. 15 years; second-pillar assets = 17.16%
of GDP. Relevance: the single most important domestic data point for this paper - direct primary
evidence that no annuity market yet exists, and for the take-up-rate denominator (total
second-pillar assets/members).

**nbrm2020fsr2019** - НБРСМ (2020), Financial Stability Report for 2019. Question: is the
domestic financial system, including private pension funds, resilient to shocks. Finding:
pension funds were (as of 2019) still accumulating, young membership, low liquidity-risk
exposure - the payout phase had barely started. Relevance: macro-prudential background for the
economy section; only the 2019 edition (published 2020) could be resolved to a working PDF URL -
newer (2023/2024) editions exist but a direct link could not be located.

**gerovskamitev2021espn** - Gerovska Mitev (2021), ESPN Thematic Report on pension adequacy for
North Macedonia, European Commission. Question: is the domestic pension system (all pillars)
adequate by EU social-policy standards. Method: qualitative/quantitative policy assessment
against the EU's pension-adequacy indicators. Relevance: domestic academic author (UKIM), EU
institutional venue - used for the economy section; does not touch mortality or annuity pricing.

**sso2023projections** - State Statistical Office (2023), *Population Projections of the
Republic of North Macedonia by 2070*. Question: what will the domestic population look like by
age/sex to 2070 under alternative fertility/mortality/migration hypotheses. Method:
cohort-component method; two deterministic mortality hypotheses (constant, or declining life
expectancy by age and sex from the 2022 level), built by abstracting away the COVID-19 mortality
shock. Finding: no quantified uncertainty band around the mortality hypothesis is published.
Relevance: the direct evidentiary basis for this paper's central novelty claim - the statistical
office uses expert deterministic hypotheses, not a stochastic model with quantified projection
uncertainty, which is exactly the gap this paper fills. Also the primary source for how the 2021
census revision was rolled into the mortality/exposure series and for why 2020-21 needs special
handling. Two dependency-related figures sometimes quoted from this report, 29.5% and 57.7%, do
both appear verbatim in it, but not as a printed "dependency ratio": 29.5% is the projected share
of the 80+ group within the 65+ population by 2070 under the constant-mortality variant, and
57.7% is a working-age-population (15-64) share-of-total-population figure from a projection-year
table; the report's own printed "Total dependency ratio (0-19+65+/20-64)" row carries different
values. Wherever 29.5%/57.7% are presented, they should be described as this paper's own
calculation from the office's underlying age-group projection data, not as a quoted published
statistic.

**raveni2024effects** - Raveni, Ismaili & Bajrami Ollogu (2024), *South East European Journal of
Sustainable Development* 8(3). Question: how does emigration affect first-pillar pension
sustainability domestically. Method: stochastic demographic/fiscal forecasting + time-series +
microsimulation. Finding: mass youth emigration significantly worsens pension sustainability;
recommends raising retirement age to 65 for both sexes. Relevance: most recent (2024) domestic
academic source on demographic/fiscal forecasting; evidence that emigration (not just mortality
improvement) drives the country's ageing profile - but it does not model mortality tables or the
second-pillar payout phase, so it cannot substitute for this paper's contribution.

**aso2026godishen** - АСО (2026), annual report on the insurance market, covering 2025. Question:
none (statistical/regulatory report). Finding: describes the legal payout-phase design
(programmed withdrawals / lifetime annuities / combination) but reports no life-annuity business
statistics for the second pillar anywhere in the 2025 market report. Relevance: corroborates
mapas2025izvestaj's "zero annuities so far" finding from the insurance-supervisor side - two
independent primary sources agree there is no annuity market yet.

**rocha2010designing / vittas2010designing** - World Bank (2010), two companion payout-phase
papers, one general and one CEE-specific. Question: what payout-phase policy options
(mandatory/voluntary annuitisation, programmed withdrawal, lump sum, combinations) suit
countries with thin insurance and capital markets. Finding: full mandatory annuitisation is
rarely advisable in thin markets; combinations with minimum-income floors are preferred; CEE
countries at the time (2010) mostly had not yet launched real annuity markets. Relevance:
directly frames the no-licence-vs-licence-exists framing and the take-up-rate scenarios
(30/60/100%) - these are exactly the "market not yet launched" conditions Vittas et al. describe
for the region 15 years ago; worth checking whether the domestic market is still in that state.

**nestic2019adequacy** - Nestić / World Bank (2019), Croatia. Croatia is the one regional case
where a mandatory-annuity payout company (via HZMO/RMOD) actually operates. Relevance: closest
operating regional comparator for what a launched second-pillar annuity market looks like -
useful contrast if the domestic market is still pre-launch.

**gubbels2007kosovo** - Gubbels, Snelbecker & Zezulin (2007), World Bank, Kosovo. Question:
early lessons from Kosovo's mandatory DC second pillar (KPST), including payout design choices.
Relevance: smallest, most comparable regional economy; shows how a small market handled (or
deferred) the annuitisation question.

**altiparmakov2018development** - Altiparmakov & Matković (2018), Serbia. Question: why did
Serbia reject mandatory second-pillar privatisation (unlike North Macedonia, Croatia, Kosovo)
and rely on voluntary + PAYG instead. Relevance: counter-example that sharpens the regional
comparison - the domestic system chose the mandatory-DC path Serbia avoided, which is part of
why the annuity question is live at all here.

**milev2020payout** - Milev (2020), Bulgaria. Question: what payout options and risks face
insured individuals as Bulgaria's universal pension funds approach payout phase. Relevance:
another CEE mandatory-DC country working through the same "how do we build the annuity payout
leg" problem contemporaneously - strengthens the claim that this is a live regional question,
not a solved one.

**sterpin2026policy** - Šterpin, Laporšek & Vovk (2026), Slovenia. Question: what welfare cost
does Slovenia's restrictive, limited-choice decumulation regime impose. Method: quantifies
welfare losses from constrained annuitisation options. Relevance: the closest 2026 regional
analogue to this paper's decumulation/take-up territory - cited prominently as evidence the
adequacy-of-decumulation-design question is an active regional research topic.

A search for Macedonian- or Serbian-language regional actuarial-journal literature applying a
stochastic mortality model (Lee-Carter/CBD family) to any Western Balkan country found none -
itself evidence for the claim that this is an actuarially unexplored region. NBRM Financial
Stability Report editions for 2023/2024 could not be resolved to a direct PDF URL within
available search tools; only the 2019 edition (nbrm2020fsr2019) is cited. The text of EU
Directive 2025/2 was not accessible via EUR-Lex automated retrieval and is not cited directly.

## Legal and institutional sources

**zakonisplata2012** - the payout law itself (Сл. весник 11/2012, 147/2015, 30/2016, 103/2021).
Statutory basis for the domestic payout-phase design (programmed withdrawal / annuity /
combination options).

**mapas2022pravilniktablici**, **mapas2022pravilnikkamatni** - the two МАПАС bylaws (177/2022)
governing mortality tables and interest rates used in payout calculations. The regulatory-
technical basis for how annuity/programmed-withdrawal amounts are actually computed
domestically.

**zpio** - Закон за пензиското и инвалидското осигурување. Член 18 confirms the retirement ages
(64/62, min. 15 years). Primary statutory confirmation of the retirement-age parameters used
throughout the paper.

**zso2022** - Закон за супервизија на осигурување. Art. 5 is the statutory basis for the finding
that no insurer is licensed for class 24 (life annuities). Legal foundation for the paper's
central "no annuity market yet" framing.

**mapas2026izvestaj** - МАПАС 2025 annual report (the edition following mapas2025izvestaj's 2024
edition). Most recent supervisory data update.

**aso2025izvestaj_xlsx** - the ASO company/segment data (distinct from aso2026godishen, the
narrative report for the same year). Underlying market-segment figures cited in the economy
section.

**aso2026registar** - the ASO life-insurer register (dated snapshot, 25 September 2026): 6
companies, classes 1/2/19/(20)/21, no class 24 anywhere in the document. The correct citation
for the paper's main finding that no insurer is licensed for class 24 (life annuities) - more
direct than the annual reports, neither of which actually names the register or class 24.

**nbrm_obvrznici** - НБРСМ government-bond auction archive. Yield-cap input for the interest-rate
bylaw calculations.

**eiopa_rfr_2026_08** - EIOPA risk-free rate term structures, 31 August 2026. Discounting input
for the capital-adequacy calculations.

**eurostat_demo_magec**, **eurostat_demo_mlifetable** - Eurostat deaths and life-table datasets.
Comparator/benchmarking data for the mortality-projection stage.

**makstat_population**, **makstat_lifetables**, **makstat_gdp**, **makstat_wages**,
**makstat_gender_pay_gap** - MAKSTAT primary datasets: population estimates, the 9 official
rolling life tables, GDP, wages, and gender pay gap. Core domestic data inputs for the mortality
and economy sections.
