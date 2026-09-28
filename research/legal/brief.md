# Legal brief - payout law and implementation status

Notes on the second-pillar payout law, its implementing bylaws and the Solvency II
provisions used in the paper, as of 25 September 2026. Primary sources are archived under
`data/raw/` (ЗПИО, ЗСО, Правилник 318/2020, EIOPA's Art. 138 text, a dated ASO register
snapshot, the МАПАС 245/2018 notice).

Law: Закон за исплата на пензии и пензиски надоместоци од капитално финансирано пензиско
осигурување ("Службен весник на Република Македонија" бр. 11/2012, 147/2015, 30/2016 и
"Службен весник на Република Северна Македонија" бр. 103/2021). Unofficial consolidated
text (МАПАС, мај 2021):
https://mapas.mk/wp-content/uploads/2021/07/Закон-за-исплата-на-пензии-и-пензиски-надоместоци-консолидиран-текст-2021-maja.pdf
**Status: CONFIRMED** (full text, 36 pages).

No amendment to this law found after 103/2021, and no active 2024-2026 draft/consultation
found. `mapas.mk/predlozen-zakon/` is the original 2012 bill announcement (Minister Spiro
Ristovski), not a new draft - **NOT FOUND** (no post-2021 amendment or live draft).

## A. Payout law

### A1. Payout types and providers - CONFIRMED

Член 3(1): second-pillar pension is paid only via one of:
а) доживотен непосреден ануитет (insurer);
б) програмирани повлекувања (pension company);
в) привремени програмирани повлекувања во комбинација со доживотен одложен ануитет
(pension company + insurer, jointly).
Член 21(1): normally single-life only; Член 21(2)/Член 5: guaranteed annuities may name
multiple successive beneficiaries.

### A2. Mortality tables and interest rates - Член 22 (full text, 7 paragraphs) - CONFIRMED

> "(1) Минималните стандарди и правилата за определување на таблици на смртност ги
> определуваат АСО и МАПАС под исти услови за друштвата за осигурување и пензиските
> друштва, имајќи ги предвид: а) специфичноста на популацијата составена од пензионери
> кои земаат пензија преку ануитет и нивните корисници и б) подобрувањето на
> долговечноста.
> (2) АСО ги пропишува правилата и минималните стандарди [sic - official text: "стандради"]
> за пресметка на технички резерви, а друштвото за осигурување е должно за пресметка на
> резервите за ануитетите да користи таблици на смртност согласно со минималните
> стандарди пропишани од АСО.
> (3) МАПАС ги пропишува правилата и минималните стандарди за таблиците на смртност, а
> пензиското друштво е должно за пресметување на ануитетниот фактор за пензии од втор
> столб преку доживотни и привремени програмирани повлекувања, да користи таблици на
> смртност согласно со минималните стандарди пропишани од МАПАС.
> (4) Друштвата за осигурување и пензиските друштва водат евиденција и статистички
> податоци за фактичката смртност на корисниците на пензија и се должни статистичките
> податоци да ги доставуваат до АСО и МАПАС во период и форма пропишани од АСО и МАПАС.
> (5) Минималните стандарди и правилата за определување на каматните стапки ги
> определуваат АСО и МАПАС под исти услови за друштвата за осигурување и пензиските
> друштва, имајќи ги предвид: а) каматната стапка која се користи за пресметка на
> резервите, односно ануитетниот фактор која не може да биде поголема од преовладувачката
> пазарна реална стапка на принос на долгорочните должнички хартии од вредност и б)
> долгорочните и среднорочните реални стапки на принос се засноваат на преовладувачките
> номинални пазарни стапки на принос за долгорочните и среднорочните должнички
> инструменти намалени за процената на стапката на трошоците за живот за истите периоди
> и на процена на идните преовладувачки пазарни стапки за долгорочните и среднорочните
> безризични должнички хартии од вредност, застапени во портфолијата на пензиските
> фондови и осигурителните друштва.
> (6) АСО ги пропишува правилата и минималните стандарди за определување на каматни
> стапки, а друштвото за осигурување е должно за пресметка на резервите за ануитетите да
> користи каматни стапки согласно со правилата и минималните стандарди пропишани од АСО.
> (7) МАПАС ги пропишува правилата и минималните стандарди за определување на каматни
> стапки, а пензиското друштво е должно за пресметка на ануитетниот фактор за пензии од
> втор столб преку доживотни и привремени програмирани повлекувања да користи каматни
> стапки согласно со правилата и минималните стандарди пропишани од МАПАС."

(Source: unofficial consolidated text, мај 2021, as linked above, pp. 11-12. All seven
paragraphs quoted verbatim.)

**Programmed withdrawals and mortality tables:** the reading "Programmed withdrawals (paid
by pension companies) do not use mortality tables" is **wrong** for second-pillar lifelong/temporary
programmed withdrawals - Art. 22(3) and the 2022 MAPAS bylaw (below) explicitly require a
mortality-table-based annuity factor for them. The "no mortality tables" rule (definition
22, чл. 2) applies only to third-pillar voluntary **"Повеќекратна исплата"** (a lump-sum
multi-instalment drawdown), a narrower, different product.

Art. 9(1): the insurance company itself chooses the tables, interest-rate assumptions,
management-cost assumptions and other pricing assumptions, subject to the Art. 22 minimum
standards.

### A3. Unisex vs sex-specific pricing - CONFIRMED (sex-specific, not unisex)

No article in the payout law itself uses the word "пол" to ban or mandate unisex pricing.
But: Art. 29(3) requires the pension company's quotation request to the Центар за котација
to include "полот и датумот на раѓање на членот" (sex and date of birth) - i.e. quotes are
generated per sex. Decisively, Art. 3 of the 2022 MAPAS mortality-table bylaw (§B1 below)
states explicitly: **"Таблиците на смртност се специфицирани по пол и возраст. Таблиците на
смртност не вклучуваат други критериуми освен возраста и полот на пензионерот."**
(mortality tables are sex- and age-specific and use no other rating factor). North
Macedonia is not EU/EEA, so the *Test-Achats* unisex ruling (C-236/09) does not apply.
**Conclusion: pricing is sex-specific by design, at least on the pension-company
(programmed-withdrawal) side; the law's data-collection design implies the same for
insurer annuities, though no ASO-side bylaw was found to confirm it for that side
specifically (see B1).**

### A4. Commission cap - CONFIRMED

Art. 8(2): "Највисокиот износ на провизија за продажба на ануитет за втор столб кој може
да се наплати од друштво за осигурување изнесува 2,5% од премијата."

### A5. Indexation - CONFIRMED

Art. 6: fixed annuities indexed to cost of living (CPI, twice yearly) or by a fixed nominal
adjustment set at purchase (unchanged for the policy's life). ASO (with MAPAS's prior
consent) sets a **minimum** nominal adjustment annually, published on aso.mk, "не може да
биде помал од 1% ниту поголем од 3%" on an annual basis.

### A6. Guarantee period / joint-life - CONFIRMED

Art. 5(3): "Гарантираниот период за ануитет е со времетраење од најмногу 240 месеци" (20
years max). Guaranteed annuities may name one or several successor beneficiaries in order
(Art. 5(1)-(2)).

### A7. What happens with no insurer offering annuities - CONFIRMED (indirect)

The law has no explicit "if no insurer bids" clause. The **practical fallback** is Art. 35:
if a member does not choose a payout type within 3 years of first-pillar retirement, they
automatically become a lifelong programmed-withdrawal recipient via their pension company
- i.e. the pension-company channel (no insurer needed) is the structural default.
Consistent with this, 100% of second-pillar payouts to date have in fact been via
programmed withdrawal (§B3).

## B. Implementation status (September 2026)

### B1. ASO/MAPAS minimum mortality-table standards - CONFIRMED, split finding

**MAPAS side: issued.** Two bylaws, both "Службен весник на РСМ" бр. 177/2022 (8.8.2022),
adopted by MAPAS Совет на експерти 27.7.2022, in force the day after publication:
- Правилник за правилата и минималните стандарди за таблиците на смртност -
  https://mapas.mk/wp-content/uploads/2022/10/pravilnik-za-pravilata-i-minimalnite-standardi-za-tabliczite-na-smrtnost.pdf
  (repeals an earlier 34/2014 version). Requires latest official state mortality tables,
  allows adjustment for own experience data or more conservative tables, requires the
  pension company to take future longevity improvement into account when setting the
  tables, and separately caps how far it may adjust for that improvement: "може да го
  продолжи очекуваното траење на живот **најмногу** до три години" - i.e. **up to 3 years
  of e_x is a ceiling on the allowed adjustment, not a required minimum.**
  **This ceiling is an argument in the paper's favour**: if the data-driven improvement
  assumption implies more than +3 years, the bylaw's cap would force pension companies to
  under-reflect it, understating reserves relative to what a cohort/projected table would
  show - directly supporting H2. Tables are sex- and age-specific only (Art. 3, quoted
  above).
- Правилник за правилата и минималните стандарди за определување на каматни стапки -
  https://mapas.mk/wp-content/uploads/2022/10/pravilnik-za-pravilata-i-minimalnite-standardi-za-opredeluvane-na-kamatni-stapki.pdf
  Caps the real rate at ≤80% of a nominal rate itself capped by domestic 5y+ government
  bond yields and the fund's own 3-year average return.

Both bylaws implement Art. 22(3)/(7) - i.e. they bind **pension companies'** annuity-factor
calculation for programmed withdrawals, not insurers.

**ASO side: no Art. 22(2)/(6) joint standard.**
No dedicated bylaw implementing Art. 22(2)/(6) was located, but ASO's general "Правилник за
минималните стандарди за пресметка на техничките резерви" (Сл. весник 318/2020, adopted
22.12.2020; archived at `data/raw/aso/pravilnik-tehnicki-rezervi-sl-vesnik-318-2020.pdf`
with OCR text alongside it) does contain relevant annuity-reserve provisions. Point
5.3.3(2) (Таблици на веројатност): **"Кај договорите за осигурување кај кои претпоставката
за намалување на смртноста ја зголемува математичката резерва, при одредување на
веројатноста за смрт за целите на процена на математичката резерва треба да биде
соодветно коригирана со цел да бидат опфатени и очекуваните идни намалувања/зголемувања
на смртноста."** - i.e. for annuity-type contracts (falling mortality raises the reserve),
the probability of death **must** be corrected for expected future mortality
improvement - a genuine, existing qualitative obligation. Point 5.3.2(2)-(3) (Каматна
стапка) separately impose a hard quantitative cap: the reserving rate may not exceed (2)
the insurer's own realised 3-year average return on the assets covering the reserve, nor
(3) the contractually guaranteed rate for that specific policy.

So ASO **does already** require (a) a forward-looking mortality-improvement correction and
(b) a quantitative interest-rate ceiling for any annuity-type reserve. **What is still
missing, precisely**, is the Art. 22(2)/(6) joint standard itself: no sex/age
specification (contrast МАПАС's Art. 3, above), no numeric threshold or floor on the size
of the improvement correction (contrast МАПАС's 3-year cap), no second-pillar scope, and
no cross-reference to Art. 22 or to МАПАС anywhere in the 318/2020 text (checked by full
OCR keyword search). **The recommendation, stated precisely: North Macedonia
has no *joint minimum standard under Art. 22* for insurer-side annuity mortality tables -
not "no requirement of any kind."** Plausibly unissued because, per B2, no insurer has yet
sought the class-24 licence it would apply to.

### B2. Annuity licence - CONFIRMED: no insurer holds it

Primary source: ASO's live register of life insurers, aso.mk/registar/osiguruvane-na-zhivot
(accessed 2026-09-22; dated snapshot archived 2026-09-25). Six licensed life
insurers, with their exact licensed classes:

| Company | Classes |
|---|---|
| Кроациа Осигурување - Живот АД | 1, 2, 19, 21 |
| Граве | 1, 2, 19, 21 |
| Винер Лајф-Виена Иншуренс Груп | 1, 2, 19, 21 |
| Сигал Лајф АД | 1, 2, 19, 20, 21 |
| Триглав Осигурување Живот АД | 1, 2, 19, 21 |
| Прва Живот АД | 1, 2, 19, 21 |

Class 24 ("Осигурување на ануитети за корисници на пензии од задолжително капитално
финансирано пензиско осигурување") is defined in Art. 5 of the Закон за супервизија на
осигурување (Сл. весник, неофицијален пречистен текст вклучувајќи 173/2022;
https://aso.mk/wp-content/uploads/2020/02/zso-neoficijalen-precisten-so-173-2022.pdf) as a
class distinct from ordinary life insurance (class 19). **None of the six licensed life
insurers holds class 24.** This matches sava-penzisko.mk (accessed 2026-09-22): "Модалитетите
[б) и в)] ќе се применуваат откако ще биде издадена првата дозвола [за класата ануитети]."
**-> Readiness framing: as of September 2026, no insurer is licensed for the annuity class, so
insurer-provided lifelong immediate annuities and the deferred-annuity combination are not
actually on the market.**

### B3. Second-pillar pensioner numbers, by payout type - three dated figures, CONFIRMED/SECONDARY

Three dated figures exist; any sentence quoting a count must use the one matching its own
reference date.

**End-2024 - CONFIRMED.** МАПАС 2024 годишен извештај (Table 5.12, "Остварени пензии и
исплати за членовите во втор столб во 2024 г."):
https://mapas.mk/wp-content/uploads/2025/09/izveshtaj-kfpo_2024_web.pdf - cumulative
through end-2024: 122 disability pensions and 329 family pensions (transferred out to
Фондот на ПИОСМ, so stop being MAPAS-side payouts), **71 old-age pensioners on programmed
withdrawal** (35 newly started in 2024) plus 1 family-member on temporary programmed
withdrawal, 6 lump-sum member payouts, 123 inherited lump sums. Zero annuity payouts. Text:
"во 2024 година, се исплаќаше старосна пензија од втор столб, преку програмирани
повлекувања, за вкупно 71 пензионирани членови."

**End-2025 - CONFIRMED.** Same report series, next edition: МАПАС 2025 годишен извештај,
pp. 66-67 (`data/raw/mapas/izvestaj-kfpo-2025.pdf`, Table 5.12 - note the table's own
caption still misprints "...во 2024 г." even though its data are for 2025, a source-side
labelling error in the source): cumulative through end-2025: 91 disability + 263
family pensions transferred out, **116 old-age pensioners on programmed withdrawal** (51
newly started in 2025) plus 1 family-member on temporary programmed withdrawal (cumulative
4 such family members), 2 lump-sum member payouts, 126 inherited lump sums. Still **zero
annuity payouts**. Text: "во 2025 година, се исплаќаше старосна пензија од втор столб,
преку програмирани повлекувања, за вкупно 116 пензионирани членови." Report also states
the second pillar is in its "дваесетте години на постоење... заклучно со 2025 година"
(twentieth year), consistent with the 2005/2006 start already established.

**30.06.2026 - SECONDARY** (news citing MAPAS, not the primary release itself):
republika.mk, 30.07.2026,
https://republika.mk/vesti/ekonomija/mapas-so-informaczija-za-tekovnite-korisniczi-koi-ostvaruvaat-isplata-na-penzija-od-vtor-penziski-stolb/
- "Со пресек на 30.06.2026 година, вкупниот број на корисници кои остваруваат исплата од
задолжителното капитално финансирано пензиско осигурување изнесува 147 лица" (113 на
минимална пензија, 34 над минималната; average monthly net payout 9,878 МКД). Payout-type
split not given in this source; no annuity licensing news reported. 71->116->147 is a
consistent, plausible growth path (system still young, cohorts only now reaching 64/62),
which is itself worth a sentence in the paper's institutional-context framing.

Second pillar start: companies licensed 2005 (МАПАС, меѓународен јавен тендер), funds
operating from 2006 (МАПАС 2024 извештај, p.16, data series begin 2006). **CONFIRMED.**

## C. Retirement parameters - CONFIRMED

Закон за пензиското и инвалидското осигурување, консолидиран текст (mapas.mk):
https://mapas.mk/wp-content/uploads/2024/03/zakon-za-penziskoto-i-invalidsko-osiguruvane.pdf
Член 18: "Осигуреникот стекнува право на старосна пензија кога ќе наполни 64 години живот
(маж), односно 62 години живот (жена) и најмалку 15 години пензиски стаж." Same conditions
apply to first- and second-pillar retirement (МАПАС 2024 извештај §5.8, echoing Art. 18).
Special/early-retirement reductions exist (Art. 19 onward) - not pursued further, out of
scope for RQ2's ages 64/62. Second-pillar-only retirement (no first-pillar right) requires
age 65 (payout law Art. 34(2)).

### C1. First-pillar/second-pillar contribution split - CONFIRMED

Baseline (2025 and normal years): total mandatory pension-and-disability contribution
(Закон за придонеси од задолжително социјално осигурување) = **18.8%** of gross wage, of
which a fixed **6 percentage points** go to the member's individual second-pillar account
(Закон за задолжително капитално финансирано пензиско осигурување) and the remaining
**12.8 p.p.** stay in the first pillar (PAYG). This is the correct figure for 2025.

**Temporary change for July-December 2026 wages - CONFIRMED via primary government
source.** Закон за изменување и дополнување на Законот за придонеси од задолжително
социјално осигурување, Сл. весник на РСМ бр. 148/2026 (6.7.2026), quoted directly (via
secondary reporting of the statutory language) as: "се врши привремена промена
(зголемување) во висината на стапката за придонесот за задолжително пензиско и
инвалидско осигурување од 18,8% на 19,9%" (offset by cutting the unemployment-insurance
contribution from 1.2% to 0.1%, so the combined 28% total rate is unchanged), applicable
"почнувајќи со исплатата на платата за месец јули 2026 година, заклучно со исплатата на
платата за месец декември 2026 година." Confirmed directly from a primary government
source: УЈП (Public Revenue Office) own notice,
https://www.ujp.gov.mk/-/javnost/soopstenija/pogledni/1266, which states the 19.9% rate
and the July-December 2026 application window in its own voice (not just citing the
gazette). The gazette itself (slvesnik.com.mk) is paywalled; the УЈП notice is a primary
government source, not press commentary, so this is marked CONFIRMED rather than SECONDARY.

The second-pillar contribution rate (6 p.p.) is set by a different law and **is not
touched** by 148/2026, which only amends the total-PIO/unemployment split. **So for a
second-pillar member's July-December 2026 wages, the first-pillar share is 19.9% − 6% =
13.9%, not 12.8%.** Both figures belong in the paper, dated - see `results/legal.json`
for the machine-readable keys.

## D. Solvency II longevity treatment

### D1. Longevity shock, Art. 138 - CONFIRMED

Text taken from EIOPA's Solvency II Single Rulebook, which reproduces the legal text of the
Delegated Regulation; archived at `data/raw/eu/eiopa_article138_longevity_risk.html`. Delegated Regulation (EU)
2015/35, Art. 138 (Longevity risk sub-module), full text:

> "1. The capital requirement for longevity risk referred to in Article 105(3)(b) of
> Directive 2009/138/EC shall be equal to the loss in basic own funds of insurance and
> reinsurance undertakings that would result from an instantaneous permanent decrease of
> 20 % in the mortality rates used for the calculation of technical provisions.
> 2. The decrease in mortality rates referred to in paragraph 1 shall only apply to those
> insurance policies for which a decrease in mortality rates leads to an increase in
> technical provisions without the risk margin. The identification of insurance policies
> for which a decrease in mortality rates leads to an increase in technical provisions
> without the risk margin may be based on the following assumptions: (a) multiple
> insurance policies in respect of the same insured person may be treated as if they were
> one insurance policy; (b) where the calculation of technical provisions is based on
> groups of policies as referred to in Article 35, the identification of the policies for
> which technical provisions increase under a decrease of mortality rates may also be
> based on those groups of policies instead of single policies, provided that it yields a
> result which is not materially different.
> 3. With regard to reinsurance obligations, the identification of the policies for which
> technical provisions increase under a decrease of mortality rates shall apply to the
> underlying insurance policies only and shall be carried out in accordance with
> paragraph 2."

Not listed among the provisions amended by the October-2025 Commission Delegated
Regulation (D2): that regulation's explanatory memorandum and recitals enumerate every
amended item (climate-related risk, risk margin/CoC, extrapolation, etc.) and Art. 138 is
absent from it. **Unchanged.**

### D2. Cost-of-capital rate after the 2025 review - CONFIRMED

Primary source: European Commission, Delegated Regulation amending Delegated Regulation
(EU) 2015/35, C(2025) 7206 final/2, Brussels, 29.10.2025:
https://ec.europa.eu/finance/docs/level-2-measures/solvency2-delegated-regulation-2025-7206_en.pdf
Point (9): "Article 39 is replaced by the
following: 'Article 39 Cost-of-Capital rate. The Cost-of-Capital rate referred to in
Article 77(5) of Directive 2009/138/EC shall be assumed to be equal to 4.75%.'" - **down
from 6%.** Recital (9): "Directive (EU) 2025/2 reduces the cost-of-capital rate underlying
the risk margin calculation, leading to an overall reduction in its level by approximately
21%." A new exponential, time-dependent tapering factor is also introduced (recital 9:
"ensures an annual reduction of risks of at least 3.5%"), to correct double-counting of
naturally-declining risks (incl. mortality/lapse) alongside the CoC cut. **Application
date: "It shall apply from 30 January 2027"** (Regulation, final article) - matching
Directive (EU) 2025/2's national transposition deadline of 30.01.2027. **So as of September
2026 the still-legally-in-force EU rate is 6%; 4.75% is adopted but not yet applicable.**
Both numbers belong in the paper, dated.

### D3. North Macedonia's insurance law vs Solvency II - NOT FOUND / weak

No confirmed evidence of a draft new Macedonian insurance law aligned with Solvency II
circulating in 2025-2026 was found. Current law (Закон за супервизија на
осигурување) remains Solvency-I-style (fixed margins; the 318/2020 technical-reserves
bylaw and the 25-class list are its main relevant provisions, §B1/B2). Note: an
ASO-published paper "Капитална ефикасност и регулаторни импликации во осигурителниот
сектор на Северна Македонија: Емпириска анализа на Солвентност I и симулација на
Солвентност II" exists on aso.mk (a 2025 ASO award paper) and is relevant to the
literature review. Whether a Solvency-II-aligned draft law exists remains an open point
for the discussion section.
