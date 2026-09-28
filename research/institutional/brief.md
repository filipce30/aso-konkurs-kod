# Institutional brief - Macedonian economy context

Narrative context for the introduction; quantitative time series are built separately from
the sources listed in `data/raw/SOURCES.csv`. Sources are given so the figures below can be
cross-checked.

## Three-pillar pension system

- First pillar: PAYG, defined-benefit, administered by Фондот на пензиското и
  инвалидското осигурување на Северна Македонија (ПИОСМ/Фонд на ПИОМ).
- Second pillar: mandatory funded, individual accounts, two pension companies (currently
  САВА пензиско друштво and КБ Прво пензиско друштво, plus a third fund brand,
  Триглав, per МАПАС 2024 report Table 5.12). Companies licensed 2005, operating since
  2006 (МАПАС 2024 годишен извештај, p.16 - CONFIRMED, see legal brief §B3).
- Third pillar: voluntary funded (individual and/or occupational accounts), same
  pension companies, launched later than the second pillar (exact launch year to be taken
  from МАПАС primary sources).
- Contribution split (first vs second pillar): 18.8% total pension contribution, of which
  6 p.p. to the second pillar; temporarily 19.9% for July-December 2026 wages (see legal
  brief §C1 for the primary sources).

## Demographic situation

- Census 2021 (ДЗС/МАКСТАТ, conducted 5-30.9.2021): 1,836,713 resident population - widely
  reported as final, e.g. stat.gov.mk announcement referenced across multiple outlets
  (24.mk, meta.mk); **SECONDARY here** (the ДЗС release PDF itself is not cited; MAKSTAT
  series are listed in SOURCES.csv). Down roughly 185,000 from the pre-census
  ~2.02-2.08M estimate quoted by media, consistent with the pre-revision estimate
  (~2.08M at 31.12.2018).
  Implication: heavy net emigration since the 2002 census is the leading explanation
  offered in the secondary press coverage; ageing (rising median age, shrinking cohort
  sizes at working age) is the mechanism linking this to second-pillar sustainability
  and to RQ1-RQ4. Precise age-structure numbers come from the MAKSTAT series.

## Fiscal pressure on the first pillar

- Budget transfers to Фондот на ПИОМ have been rising and are reported (2026 budget
  projections, per financial press) to reach roughly 41% of the Fund's total revenue in
  2026, versus a 32.6-43.6% range over 2014-2024. 2024 transfers reported around €690m;
  2025 transfers reported to exceed €800m-€939m depending on the source and whether all
  levels of government are included. **SECONDARY only** (journalistic reporting -
  radiomof.mk, fokus.mk, provereno.mk - citing budget documents and State Audit Office
  findings; the underlying Буџет на РСМ / Државен завод за ревизија documents are not
  cited directly). Directionally consistent and reported by multiple independent outlets,
  but the exact percentages are indicative, not citable numbers, without the primary
  budget/audit document.
- Underlying driver cited by these sources: first-pillar contribution revenue alone does
  not cover pension expenditure (structural PAYG deficit), partly because ~1/3 of the
  contribution goes to the second pillar for members who joined it, and partly
  demographic (shrinking contributor base).

## Insurance market structure

- Life insurance is a minority of the total Macedonian insurance market; non-life
  (dominated by MTPL/motor) is the majority. No precise percentage split is cited:
  sources give inconsistent numbers for 2024/2025 (13.15% vs 17.3% life share quoted in
  different excerpts of the same underlying ASO annual report), and the primary ASO data
  sit in Excel attachments to aso.mk's "Годишен извештај за состојбата и движењата на
  осигурителниот пазар во 2025 година" (and the quarterly reports, which publish the
  underlying company-level Excel files).
- Six companies hold a life licence (see legal brief §B2 for the full list and their
  classes); none currently holds the second-pillar annuity class (24). This is the direct
  institutional basis of the paper's readiness framing.

## Denar/euro peg

- Народна банка на РСМ has run a de facto fixed exchange rate of the denar to the euro
  since 1997 (currently ~61.5 МКД/ЕУР), the anchor of Macedonian monetary policy, as
  stated in NBRM's own monetary-policy communications; a specific peg-rate number in the
  paper is cited to the NBRM primary source.
  Relevance to the paper: justifies using the EIOPA EUR risk-free curve as one interest-
  rate scenario for annuity pricing (methodology section), since MKD-denominated
  long-term real yields are thin and the currency itself is EUR-anchored.

## Implications for the paper (interpretation)

- The fiscal-pressure and demographic bullets above support the "why longevity risk
  matters now" framing in the introduction; the secondary figures above are cited in the
  paper only with their primary source.
- The insurance-market-structure finding (no annuity-class licence, life insurance a
  market minority) directly motivates the readiness framing and RQ4's take-up scenarios:
  liability projections are necessarily hypothetical/market-entry scenarios, not observed
  experience, which is itself a limitation stated explicitly in the paper.
