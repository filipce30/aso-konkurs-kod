# Comparators: second-pillar annuity payout regimes in Croatia, Slovakia, Latvia and Romania

**Purpose.** The paper recommends that ASO issue the minimum standards for mortality tables for
second-pillar annuities that Art. 22 of the payout law requires and that have never been issued.
This file establishes what comparable supervisors actually required when their own second pillars
reached the payout phase, so that the recommendation can be positioned against regional practice
instead of being asserted.

**Method and integrity.** Every document relied on below is archived under
`data/raw/compare_legal/<country>/` with a row in `data/raw/SOURCES.csv`. Operative provisions are
quoted verbatim in the original language with an English gloss. Status flags:

- **CONFIRMED** - primary document opened and archived (law, supervisory bylaw, supervisor or
  administering-agency website, supervisor annual report, government working-group report).
- **SECONDARY** - only a secondary source located; used to signal existence, never as evidence for
  an operative claim.
- **NOT FOUND** - searched and not located; no inference drawn.

Croatian, Slovak, Latvian and Romanian texts were read in the original. Glosses are my own
translations; where a machine translation was used as an aid this is stated. Romanian
quotations come from a scanned PDF with an OCR text layer, so diacritics in the quoted strings are
partly corrupted (`ș`->`i`, `ţ` inconsistencies); the wording itself is legible and reproduced as it
appears, with corrupted characters left as-is rather than silently "fixed".

---

## 1. Croatia

Mandatory second pillar since 2002. Since 2014 a dedicated regime of pension insurance companies
(*mirovinska osiguravajuća društva*, MOD) pays the annuities, supervised by HANFA.

Primary texts archived: `zmod_hanfa_consolidated.pdf` (Zakon o mirovinskim osiguravajućim
društvima, unofficial consolidated text NN 22/14, 29/18, 115/18, 156/23, 52/25, published by
HANFA); `nn_22_2014_zmod.html` (original gazette text); `nn_156_2023_zmod_izmjene.html`
(2023 amendments); `nn_20_2024_pravilnik_min_standardi_tehnicke_pricuve.html` (HANFA bylaw on
minimum standards for the calculation of technical provisions, NN 20/2024);
`hanfa_registar_mod.html` (register); `hanfa_isplata_mirovine.html` (HANFA consumer page);
`hanfa_godisnje_izvjesce_2024.pdf` (HANFA annual report 2024);
`mrosp_analiza_mirovinski_sustav_2024.pdf` (Ministry of Labour and Pension System, report of the
working group on the state of the pension system, 2024).

### 1.1 Who may provide the annuity, and under what licence - CONFIRMED

A dedicated legal form: the pension insurance company, licensed and supervised by HANFA. ZMOD
Art. 1 covers "osnivanje, poslovanje i prestanak mirovinskih osiguravajućih društava koja isplaćuju
mirovine u okviru obveznog i dobrovoljnog mirovinskog osiguranja na temelju individualne
kapitalizirane štednje" ("the establishment, operation and winding-up of pension insurance
companies which pay pensions within mandatory and voluntary pension insurance based on individual
capitalised savings"). Life insurers may pay third-pillar benefits but not second-pillar annuities.

HANFA register, accessed 2026-09-25: **two** licensed companies - Hrvatsko mirovinsko
osiguravajuće društvo d.d. and Raiffeisen mirovinsko osiguravajuće društvo d.d. The Ministry's 2024
working-group report states the same: "Trenutno u Republici Hrvatskoj posluju dva mirovinska
osiguravajuća društva" ("Two pension insurance companies currently operate in the Republic of
Croatia").

A retiring second-pillar member chooses between a first-pillar-only pension (their capitalised
savings are transferred to the state budget) and the combined pension, which requires a pension
contract with a MOD (working-group report, section on the second pillar; ZMOD Art. 103).

### 1.2 The mortality basis - CONFIRMED that a projected basis is used; no table prescribed

**The law does not prescribe a table.** It requires the calculation bases to be filed and reviewed.
ZMOD Art. 16(2)(9), on the content of the licence application:

> "9. računske osnovice te načela i formule za obračun mirovine, kao što su tablice vjerojatnosti
> i kamatne stope s mišljenjem ovlaštenog aktuara."

("the calculation bases and the principles and formulas for calculating the pension, such as
probability tables and interest rates, with the opinion of an authorised actuary.")

Ongoing control is ex ante and price-based, not table-based. ZMOD Art. 106:

> "(1) Društvo je dužno Agenciji dostaviti na pregled podatke o jediničnim iznosima mirovina i
> zajamčenim isplatama imenovanim korisnicima koje namjerava primjenjivati... prije njihove
> primjene.
> (2) Društvo može primjenjivati jedinične iznose... ako Agencija ne iznese primjedbe na njihovu
> primjenu u roku od 30 dana...
> (4) Podaci... moraju biti detaljno obrazloženi uzimajući u obzir gospodarske i aktuarske
> parametre na kojima se temelje predloženi jedinični iznosi, s mišljenjem ovlaštenog aktuara."

("The company must submit to the Agency for review the unit pension amounts and guaranteed payouts
it intends to apply, before applying them. It may apply them if the Agency raises no objection
within 30 days. The data must be explained in detail having regard to the economic and actuarial
parameters underlying the proposed unit amounts, with the authorised actuary's opinion.")

**The supervisor's own description of the mortality basis actually used** (HANFA consumer page
"Isplata mirovine", accessed 2026-09-25):

> "MOD-ovi koriste populacijske tablice smrtnosti koje korigiraju s obzirom na očekivani udio
> muškaraca i žena u populaciji te za očekivano produljenja trajanja života tijekom razdoblja
> isplate mirovina. Kamatna stopa koje MOD koristi određuje se s obzirom na očekivani dugoročni
> prinos na ulaganja sredstava tehničkih pričuva."

("Pension insurance companies use population mortality tables which they adjust for the expected
share of men and women in the population and for the expected lengthening of life during the period
of pension payment. The interest rate the company uses is determined with regard to the expected
long-term return on the investment of technical-provision assets.")

So: population (not annuitant) tables, blended to a unisex basis by the expected sex mix, **and
corrected for expected future mortality improvement over the payout period**. The improvement
allowance is qualitative - no rate, no generational table and no ceiling is prescribed.

HANFA's bylaw on minimum standards for technical provisions (NN 20/2024) is principles-based and
IFRS 17-oriented; it does **not** name a table. Annex I requires assumptions to be realistic,
justified, consistent over time and documented, and expressly contemplates "projekciju budućih
trendova" ("projection of future trends"). Searching the bylaw for *smrtnost* / *mortalitet* returns
no hits - **NOT FOUND**: no prescribed table, no prescribed improvement scale, no prescribed
annuitant adjustment.

**Documented gap, in the government's own words** (working-group report, 2024):

> "Jedan od problema istaknutih na radnoj skupini je nepostojanje službenih rentnih tablica
> smrtnosti u Republici Hrvatskoj. Naime, DZS ima samo opće populacijske tablice smrtnosti, dok je
> kod izračuna očekivanog doživljenja potrebno koristiti rentne tablice smrtnosti. Za izradu
> navedenih tablica potrebno je pokrenuti suradnju DZS-a s Hrvatskim aktuarskim društvom,
> Prirodoslovno-matematičkim fakultetom i HANFA-om..."

("One of the problems highlighted in the working group is the absence of official annuity mortality
tables in the Republic of Croatia. The Central Bureau of Statistics has only general population
mortality tables, whereas annuity mortality tables are needed for calculating expected survival.
Producing such tables requires cooperation between the Bureau, the Croatian Actuarial Association,
the Faculty of Science and HANFA.")

That is: ten years into a functioning annuity regime, Croatia still has no annuitant table, and its
ministry treats this as an open problem.

### 1.3 Unisex pricing - CONFIRMED (required)

ZMOD Art. 105 ("Rodna jednakost"):

> "(1) Pri izračunu mirovine koja se isplaćuje sukladno odredbama ovoga Zakona ne može se
> uspostavljati odnosno provoditi, izravno ili neizravno, nejednakost u pravu ili isključenje iz
> prava zasnovano na rodnoj razlici. (2) ...osobito se odnosi na: ... - određivanje različitih
> svota mirovine zbog različitih uvjeta primjenjivih samo na korisnike mirovine istoga spola, pri
> određivanju mirovina."

("In calculating a pension paid under this Act no inequality of right or exclusion from a right
based on gender difference may be established or applied, directly or indirectly... in particular:
determining different pension amounts because of conditions applicable only to pensioners of the
same sex.")

Reinforced by Art. 107, which exhaustively lists the permitted differentiators:

> "Jedinični iznosi mirovina i zajamčenih isplata mogu se razlikovati samo ovisno o vrsti i obliku
> mirovine, o načinu usklađivanja, o dobnoj skupini kojoj korisnik mirovine pripada i o trajanju
> zajamčenog razdoblja. Jedinični iznosi jednako se primjenjuju prema svim osobama koje žele
> sklopiti ugovor o mirovini."

("Unit amounts of pensions and guaranteed payouts may differ only by the type and form of pension,
the indexation method, the age group of the pensioner and the length of the guarantee period. Unit
amounts apply equally to all persons wishing to conclude a pension contract.")

Legal basis as listed in ZMOD Art. 2: Directives 2006/54/EC and 2010/41/EU (the ZMOD list does not
cite Directive 2004/113/EC or *Test-Achats* expressly; EU-wide unisex insurance pricing after
*Test-Achats* is the general backdrop). North Macedonia is not bound by any of this, and МАПАС's
bylaw expressly requires sex-specific tables - the opposite design.

### 1.4 Maximum interest rate or discount basis - NOT FOUND (no statutory cap)

No ceiling in ZMOD. The rate is the company's own, set "s obzirom na očekivani dugoročni prinos na
ulaganja sredstava tehničkih pričuva" (HANFA consumer page) and controlled through the Art. 106
non-objection procedure and the appointed actuary's opinion. Two quantitative constraints do exist
on the loading side and the surplus side:

- Art. 77(3)(1): "Stvarni troškovi pribave osiguranja u izračunu tehničke pričuve ne smiju
  prelaziti 3,5 % od doznake odnosno jednokratne uplate." ("Actual acquisition costs in the
  calculation of the technical provision may not exceed 3.5% of the transfer or single payment.")
- Art. 88(1)-(3): if technical-provision assets exceed 110% of all current and future obligations
  the excess may be distributed, and above 115% distribution down to 110% is mandatory, one quarter
  to intervention reserves and the remainder to pensioners.

### 1.5 Guarantee period, indexation, joint-life - CONFIRMED (mandated menu, with floors)

- Art. 112(1): the company **must** offer a lifetime monthly old-age (or early old-age) pension, a
  lifetime monthly disability pension, and a family pension.
- Art. 113(1): four forms - individual; joint (paid for life to the surviving spouse); individual
  with a guarantee period; joint with a guarantee period. Floors: the surviving spouse receives at
  least 60% of the pension paid to the pensioner (Art. 113(3)); a named beneficiary during the
  guarantee period at least 50% (Art. 113(4)).
- Art. 114: the form is **not free**. With no spouse, the member must take an individual pension
  (with or without guarantee). If the spouse is over 50, unemployed and without other regular
  income, the member must take a joint form unless the spouse consents otherwise.
- Art. 116(1)-(2): the company must offer a pension indexed to the consumer price index at least
  twice a year, and may offer a non-indexed variant **only** alongside the indexed one, with a clear
  description of inflation risk (Art. 116(3)).
- Art. 112(8)-(9): partial lump sum of at most 20% of the transfer before deduction of the
  company's fee, available only if the first-pillar basic pension exceeds the minimum pension. (The
  HANFA consumer page still states 15%; the 20% figure is the amended ZMOD text, NN 52/25, and the
  2024 working-group report confirms the increase from 15% to 20%.)

### 1.6 Commission or expense caps - partly CONFIRMED, partly NOT FOUND

Acquisition costs recognised in the technical provision are capped at 3.5% of the transfer
(Art. 77(3)(1), above). Distribution of pension programmes by third parties is permitted but
Art. 120(4) forbids the distributor from giving advice or recommending a particular programme. An
explicit cap on sales commission comparable to the Macedonian 2.5% of premium was **NOT FOUND** in
ZMOD. (For contrast, the 2023 amendments cap the *fund* management fee on the accumulation side at
0.25% of assets in 2024, declining to 0.20% from 2029 - HANFA annual report 2024, footnote 5.)

### 1.7 Take-up in practice - CONFIRMED

Working-group report, citing the Central Registry of Insured Persons (REGOS) as at 31 October 2024:

> "Do istog datuma zaprimljeno je 11.875 izjava o izboru mirovine, od čega je 7.687 (65 %)
> osiguranika izabralo mirovinu samo iz prvog mirovinskog stupa, a 4.188 (35 %) osiguranika
> izabralo mirovinu iz oba mirovinska stupa."

("By the same date 11,875 pension-choice statements had been received, of which 7,687 (65%) of
insured persons chose a pension from the first pillar only and 4,188 (35%) chose a pension from both
pillars.")

So annuity take-up ~ **35%** (4,188/11,875 = 0.3527). The report does not state whether the 11,875
statements are a 2024 flow or a cumulative stock; treat the ratio, not the level, as the usable
number.

Volumes (HANFA annual report 2024): two companies; total assets €557.5m (+30.2%); beneficiaries
21.5 thousand at end-2024 (+21.5%), of which mandatory-pillar 17.4 thousand (+30.9%) and
voluntary 4.1 thousand (−6.6%); transfers into the companies €149.6m in 2024 (+77.3%), of which
86.9% into the individual lifetime old-age pension, 6.4% temporary pension, 6.1% joint lifetime
pension.

Form chosen: "Trenutno se oko 50 % osiguranika opredjeljuje za pojedinačnu doživotnu mirovinu sa
zajamčenom isplatom kapitaliziranih sredstava" ("about 50% of insured persons currently opt for an
individual lifetime pension with a guaranteed payout of the capitalised funds") - working-group
report, which also notes that this form is not expressly provided for in ZMOD and may need
regulation.

### 1.8 Documented problems after launch - CONFIRMED

From the working-group report: (i) a declining share of new retirees choosing the two-pillar
pension, described as threatening the sustainability and purpose of the three-pillar system;
(ii) among the causes, "promjene cjenika mirovinskih osiguravajućih društava koji su rezultirali
smanjenjem iznosa mirovine s obzirom na njihovu obvezu da mirovine usklađuju sa, u tom trenutku,
rastućom inflacijom" ("changes in the pension insurance companies' price lists which reduced pension
amounts, given their obligation to index pensions to then-rising inflation") - i.e. a documented
pricing dispute in which the mandatory CPI indexation fed straight into lower quoted annuities;
(iii) the response was not to touch the actuarial basis but to raise the first-pillar supplement
from 20.25% to 27% (NN 156/23, in force 1 January 2024) to make the combined pension attractive
again; (iv) the absence of official annuitant tables (quoted in §1.2); (v) only about 2% of
first-time employees actively choose a mandatory fund.

---

## 2. Slovakia

Second pillar since 2005; annuities provided by competing life insurers, supervised by NBS, quoted
through a central offer system operated by Sociálna poisťovňa. This is the model North Macedonia
legislated and never activated, so it is the design analogue.

Primary texts archived: `zakon_43_2004_slovlex_20260101.html` and `.pdf` (Zákon č. 43/2004 Z. z.
o starobnom dôchodkovom sporení, consolidated version in force from 1 January 2026, slov-lex - the
official state legal portal); `socpoist_dozivotny_dochodok_2025.html` and `_2024.html` (Sociálna
poisťovňa statistical releases); `mpsvr_dozivotne_dochodky.html` (Ministry of Labour, Social Affairs
and Family, description of the annuity variants); `socpoist_dochodok_ii_pilier.html`.

### 2.1 Who may provide the annuity - CONFIRMED

A life insurer ("poistiteľ"), through a *zmluva o poistení dôchodku* (pension insurance contract).
The pension management company (DSS) may pay only a programmed withdrawal (§33a). Offers are
generated exclusively through the central offer system administered by Sociálna poisťovňa
(§46e(1)), are binding and irrevocable for 30 days (§46(2)), and the contract may be concluded only
on the basis of such a binding offer (§46f(5)).

Crucially, the lifetime annuity is the **default**: a temporary annuity or a programmed withdrawal
may be agreed only if the saver's other lifetime pension income plus the pillar-2 lifetime annuity
exceeds the statutory *referenčná suma* - the average old-age pension of post-2003 first-pillar
retirees (§33(2), §33a(2), §46da). Where no insurer makes an offer at all, the fallback opens
(§33(3), §33a(3)).

### 2.2 The mortality basis - CONFIRMED: a projected basis is required by statute

§46(3) (and identically §46a(3) for the temporary annuity):

> "Sumu dôchodku uvedenú v ponuke... určí poistiteľ použitím poistno-matematických metód tak, aby
> bola zabezpečená trvalá splniteľnosť záväzku poistiteľa voči poistenému. Na ohodnotenie rizika
> pri určení sumy dôchodku... použije poistiteľ vlastné vierohodné predpoklady určené na základe
> dostupných údajov, **pričom použitá pravdepodobnosť úmrtnosti zohľadňuje aj budúci demografický
> vývoj a jediným individuálnym rizikovým faktorom je vek budúceho poberateľa dôchodku.**"

("The insurer determines the pension amount stated in the offer using actuarial methods so that the
permanent fulfilability of the insurer's obligation to the insured is ensured. For the assessment of
risk when determining that amount the insurer uses its own credible assumptions based on available
data, **whereby the mortality probability used shall also take into account future demographic
development, and the only individual risk factor is the age of the future pension recipient.**")

This is the single most important comparator finding. A statute - not a bylaw, not guidance -
obliges the provider to use a forward-looking mortality assumption. It does **not** prescribe a
table, an improvement rate, a generational structure or a ceiling; it sets a qualitative
requirement plus an own-assumptions-with-supporting-data standard, policed through the offer system
and NBS supervision.

Anti-selection is handled by prohibition rather than by pricing. §46f(13):

> "Poistiteľ môže žiadať od sporiteľa informácie týkajúce sa ohodnotenia rizika dožitia poistníka
> len po uzatvorení zmluvy o poistení dôchodku. Sporiteľ nie je povinný informácie podľa
> predchádzajúcej vety poskytnúť."

("The insurer may request information relating to the assessment of the policyholder's survival risk
only after the pension insurance contract has been concluded. The saver is not obliged to provide
that information.")

The Ministry's own description confirms the practical effect: "Pri určení sumy vášho dôchodku
poisťovňa nemôže okrem vášho veku a nasporenej sumy na osobnom dôchodkovom účte zohľadniť žiadne
ďalšie individuálne faktory (ako napr. váš zdravotný stav)." ("In determining your pension amount
the insurer may not take into account any individual factors other than your age and the amount
saved in your personal pension account - such as your state of health.")

### 2.3 Unisex pricing - CONFIRMED (required, by statute)

Sex is excluded by the same clause that excludes every other rating factor: "jediným individuálnym
rizikovým faktorom je vek budúceho poberateľa dôchodku" (§46(3)). The EU *Test-Achats* obligation is
the backdrop; the Slovak statute states the rule directly and more broadly.

### 2.4 Maximum interest rate or discount basis - NOT FOUND as a cap; disclosure is mandatory

No statutory ceiling on the technical interest rate. Instead the guaranteed investment return used
in the calculation is a registered, contractual and supervised parameter:

- §46e(2)(o): the offer system processes data "o percentuálnej výške garantovaného výnosu z
  umiestnenia prostriedkov technických rezerv použitej pri výpočte mesačnej sumy dôchodku" ("on the
  percentage of the guaranteed return on the placement of technical-reserve assets used in
  calculating the monthly pension amount"), which the insurer must supply (§46e(4)).
- §46f(11): the contract must state that percentage.
- §42a(1): returns above the guaranteed rate are surplus, split between insurer and insured as
  agreed in the contract, but "časť prebytku z výnosov určená poisteným nesmie byť menej ako 90 %
  z prebytku z výnosov" ("the part of the surplus allocated to the insured may not be less than 90%
  of the surplus").

### 2.5 Guarantee period, indexation, joint-life - CONFIRMED (statutory)

- **Guarantee period is compulsory, not optional.** §32(2): if the recipient dies before 84 monthly
  payments of the lifetime annuity have been made, the difference between the amount earmarked for
  those 84 payments and the sum actually paid goes to the designated person. The Ministry states it
  plainly: "Každý z variantov doživotného dôchodku A - D obsahuje 7 ročnú garanciu výplaty." ("Each
  of the lifetime-annuity variants A-D contains a 7-year payout guarantee.")
- **A fixed menu of six offer variants** is compulsory (§46(1)(a)): with/without indexation,
  crossed with no survivor cover, one-year survivor cover, two-year survivor cover.
- **Indexation rate is set in law, not by the insurer.** §42(1)-(2): the annual increase applies at
  the percentage valid on the date of the offer, and NBS may set that percentage by measure, taking
  into account the primary objective of the ECB. Transitional provision §123ao(3): "Percento
  zvyšovania doživotného starobného dôchodku... podľa § 42 je 2 %, ak Národná banka Slovenska
  opatrením podľa § 42 ods. 2 neustanoví inak." ("The percentage of increase... is 2% unless NBS
  provides otherwise by measure.")
- Survivor pension is paid at the full amount of the annuity the deceased was receiving, for one or
  two years as chosen (§34(2), §36(1)) - a short-duration widow/widower cover rather than a
  perpetual joint-life annuity.

### 2.6 Commission or expense caps - CONFIRMED, and stricter than a cap

§46f(16): "V súvislosti s uzatvorením zmluvy o poistení dôchodku sa nesmie vykonávať finančné
sprostredkovanie podľa osobitného predpisu." ("In connection with the conclusion of a pension
insurance contract, financial intermediation under the special legislation may not be carried out.")
§46f(15) also forbids bundling unrelated goods and services, and §46f(10) forbids any surrender
charge. Effectively a zero-commission regime: there is no distribution channel to pay.

### 2.7 Take-up in practice, and whether the market attracted providers - CONFIRMED

Sociálna poisťovňa, release of 22 January 2026, on calendar year 2025:

> "Priemerná výška doživotných dôchodkov z II. piliera vyplácaných životnými poisťovňami, bez
> indexácie a bez pozostalostného krytia, predstavovala za rok 2025 sumu 26,20 EUR mesačne (v roku
> 2024 to bolo 24,55 EUR). Celkovo poberalo minulý rok dôchodok z II. piliera formou doživotného
> dôchodku 9 852 sporiteľov. ... Počet uzatvorených zmlúv so životnou poisťovňou na doživotný
> dôchodok za obdobie roka 2025 predstavoval 2 588. Popri doživotnom dôchodku bolo uzatvorených
> ďalších 361 dohôd o vyplácaní dôchodku z II. piliera programovým výberom. Možnosť použiť celú
> nasporenú sumu príspevkov - v prípade splnenia podmienky poberania dôchodkov aspoň vo výške
> referenčnej sumy - na programový výber (vrátane jednorazového vyplatenia príspevkov), využilo
> minulý rok 7 800 sporiteľov. V režime malá nasporená suma bolo v roku 2025 uzatvorených 1 028
> zmlúv. Týmto sporiteľom neponúkla žiadna poisťovňa doživotný dôchodok z dôvodu nízkej nasporenej
> sumy. Preto im bude dôchodková správcovská vyplácať dôchodok mesačne najviac v sume 14,90 eura až
> do vyčerpania nasporenej sumy (nie doživotne)."

("The average lifetime annuity from the second pillar paid by life insurers, without indexation and
without survivor cover, was €26.20 per month in 2025 (€24.55 in 2024). In total 9,852 savers
received a second-pillar pension in the form of a lifetime annuity last year. ... The number of
lifetime-annuity contracts concluded with a life insurer in 2025 was 2,588. Alongside a lifetime
annuity, a further 361 agreements on programmed withdrawal were concluded. The option of using the
entire saved amount for programmed withdrawal - where the condition of receiving pensions at least
equal to the reference amount is met - including a single payment, was used by 7,800 savers last
year. Under the small-saved-amount regime, 1,028 contracts were concluded in 2025. No insurer
offered these savers a lifetime annuity because of the low amount saved. The pension management
company will therefore pay them at most €14.90 per month until the saved amount is exhausted, not
for life.")

Also: 14,559 applications for a second-pillar pension in 2025 (20,692 in 2024).

Take-up on the cleanest available denominator - new payout decisions in 2025 - is
2,588 / (2,588 + 7,800 + 1,028) = **22.7%**. On the applications denominator it is 2,588/14,559 =
17.8%; applications and concluded contracts do not map one-to-one within a calendar year, so the
first ratio is the one to use, with the denominator stated.

Number of insurers actually participating in the offer system: **NOT FOUND** from a primary source
(searched socpoist.sk and employment.gov.sk; the offer list is generated per
saver and the participating-insurer list was not located as a published register).

### 2.8 Documented problems after launch - CONFIRMED

1. **Small balances get no offer at all.** 1,028 savers in 2025 received no lifetime-annuity offer
   from any insurer because the saved amount was too low, and fell back to a statutory
   drawdown capped at €14.90 per month until exhaustion. The minimum monthly amount each insurer
   is willing to pay is itself a registered parameter of the offer system (§46e(8)), and Sociálna
   poisťovňa publishes its median (§46e(9)). This is a market failure the legislator anticipated and
   priced into the statute rather than solved.
2. **Very low annuity levels** (€26.20 average in 2025) - the same maturity problem North Macedonia
   will face, since contributions began in 2005 there and 2006 here.
3. **Structural selection.** Because annuitisation is compulsory below the reference amount and
   optional above it, the annuitant pool is tilted towards savers with low other pension income;
   the statutory ban on any rating factor other than age (§46(3)) and on pre-contract health
   questions (§46f(13)) means insurers cannot respond to that by underwriting, only through the
   general mortality assumption.

---

## 3. Latvia

Second-pillar capital may be used to buy a life annuity policy from a licensed life insurer, with
the State Social Insurance Agency (VSAA) as the contracting party. The premise that this started in
2020 is **imprecise** and should not be repeated in the paper: the option and its standard terms
date from 2003, the standard-terms regulation was repealed in 2012, and the 2018-2021 amendments
reorganised the choice and added a legacy clean-up exercise in 2020-2021.

Primary texts archived: `valsts_fondeto_pensiju_likums.html` (State Funded Pension Law, consolidated
text on likumi.lv, the official publisher); `mk272_fondeto_pensiju_shemas_darbiba.html` (Cabinet
Regulation No. 272 of 27 May 2003 on the operation of the state funded pension scheme);
`muza_pensijas_tipveida_noteikumi_repealed.html` (Cabinet Regulation No. 106 of 11 March 2003,
standard terms of life pension insurance - in force 19.03.2003, repealed 29.04.2012);
`vsaa_transfer_2nd_pillar_annuity_en.html` (VSAA service description). Latvian read in the original
with machine-translation support for the procedural paragraphs.

### 3.1 Who may provide the annuity - CONFIRMED

State Funded Pension Law Art. 7(1): on claiming the old-age pension (including early) the member
chooses one of two options:

> "1) uzkrāto fondētās pensijas kapitālu pievienot nefondētajam pensijas kapitālam, lai aprēķinātu
> vecuma pensiju saskaņā ar likumu 'Par valsts pensijām';
> 2) par uzkrāto fondētās pensijas kapitālu iegādāties dzīvības apdrošināšanas (mūža pensijas)
> polisi. Šādā gadījumā dzīvības apdrošināšanas (mūža pensijas) līgumā tiek noteikts mūža pensijas
> mēneša apmērs, kas tiek izmaksāts visā mūža pensijas izmaksas periodā, un apdrošināšanas
> sabiedrība par tā apmēru informē Aģentūru."

("1) add the accumulated funded pension capital to the unfunded pension capital in order to
calculate the old-age pension under the law 'On State Pensions'; 2) purchase a life insurance
(lifetime pension) policy with the accumulated funded pension capital. In that case the life
insurance (lifetime pension) contract sets the monthly amount of the lifetime pension, which is paid
throughout the lifetime pension payment period, and the insurance company informs the Agency of that
amount.")

Art. 7(1¹): "Dzīvības apdrošināšanas (mūža pensijas) polises iegādes kārtību nosaka Ministru
kabinets." ("The procedure for purchasing the policy is determined by the Cabinet of Ministers.")
The fixed-for-life monthly amount requirement in Art. 7(1)(2) took effect on 1 January 2023
(transitional provision 30). The provider is an ordinary licensed life insurer; there is no
dedicated legal form.

### 3.2 The mortality basis - NOT FOUND (nothing is prescribed)

Neither the law nor Cabinet Regulation No. 272 mentions mortality (*mirstība*), a table, life
expectancy or an improvement assumption: searching both texts returns no hits. The repealed standard
terms (Regulation No. 106/2003) likewise prescribed no mortality basis; they regulated contract
structure only - the insurer computes the possible annuity from the premium and the data on the
insured person (§5), a co-insured spouse may be named and is taken into account in the amount (§6),
no surrender value (§10), at most three payment phases with the first at least five years and at
most half of the premium paid out during it (§12).

Conclusion for Latvia: the mortality basis is left entirely to the insurer under Solvency II
best-estimate principles and Latvijas Banka's general insurance supervision. **No prescribed table,
no required projection, no ceiling.** This is a genuine NOT FOUND, not an omission in the search:
the two instruments that could contain such a rule were read in full.

### 3.3 Unisex pricing - inferred from EU law only

No provision in the State Funded Pension Law or Regulation No. 272. EU law (*Test-Achats*, Directive
2004/113/EC as interpreted in C-236/09) requires gender-neutral premiums in Latvia as in any member
state, but the Latvian instrument establishing it is the insurance-contract/equal-treatment
legislation, which is not examined here. **NOT FOUND in the pension instruments**; Latvia is not
cited as a positive example of an express unisex rule.

### 3.4 Structural features that matter for Macedonia - CONFIRMED

Cabinet Regulation No. 272, as amended:

- §67: within 10 working days of the old-age pension being granted, VSAA sends the member the list
  of insurers licensed and offering the service, links to their calculators, **"apdrošināšanas
  sabiedrību noteiktais minimālais uzkrātās fondētās pensijas kapitāla apmērs, kas dod tiesības
  iegādāties mūža pensijas polisi"** (§67.4 - "the minimum amount of accumulated funded pension
  capital set by the insurance companies that gives the right to purchase a lifetime pension
  policy"), the contracting procedure and the deadline.
- §67¹: insurers must maintain public calculators and ensure that the amount stated in the issued
  policy does not differ from the projected amount offered by the calculator.
- §67²: the member has five months from the grant of the old-age pension to conclude the contract.
- §68: if the member asks to add the capital to the unfunded capital, **or if the accumulated
  capital is below the insurers' minimum**, the capital goes to the state pension special budget and
  the first-pillar pension is calculated or recalculated instead.
- §70: VSAA concludes a contract with each insurer governing the procedure, information exchange and
  premium transfer.
- Law Art. 9(2)(2): the Ministry of Welfare may require quarterly reports from insurers on the
  annuity services provided, the dynamics of participant numbers and annuity amounts.

So Latvia, like Slovakia, legislates around the small-balance problem by letting insurers set a
minimum premium and routing everyone below it back into the public pillar.

### 3.5 Take-up and providers - NOT FOUND (primary); secondary figures deliberately not used

VSAA's statistics pages were searched and no published series on the number of annuity policies
purchased versus capital added to the first pillar was located. Secondary sources
(LV portāls / industry commentary) give figures for policies in force and name two providers with a
€2,000 minimum capital, but these are **SECONDARY** and are recorded here only as pointers;
they are not used in the paper. The researchable primary route is VSAA's
statistical data portal and the Ministry of Welfare's annual review of pillar 2 and 3 results.

---

## 4. Romania

The common description of Romania - second pillar since 2008 and still no payout law - **was true
until the end of 2025 and is now out of date.** Romania enacted its payout law in January 2026, roughly eighteen
years after contributions started.

Primary texts archived: `senat_25L214FP_forma_promulgata.pdf` (the promulgated form of the Law on
the payment of private pensions, file 25L214FP from the Senate's legislative record for L214/2025,
i.e. the text as promulgated after re-examination) and `senat_25L214FG_forma_initiatorului.pdf` (the
initiator's text, for comparison). Both are scanned PDFs with an OCR layer; quotations below
reproduce the OCR output, in which some Romanian diacritics are corrupted.

**Publication reference - SECONDARY.** Multiple legal and industry sources give the promulgated law
as *Legea nr. 2/2026 privind plata pensiilor private*, Monitorul Oficial Part I no. 2 of 5 January
2026. The official gazette text (`legislatie.just.ro`) and the ASF site (`asfromania.ro`) were not
accessible, so the number "2/2026" and the gazette citation are
**SECONDARY** while the *content* quoted below is CONFIRMED from the Parliament's own promulgated
text. The final article numbering should be checked against the gazette before article numbers
are cited.

### 4.1 Who may provide the annuity - CONFIRMED

Art. 4(1): providers that may manage private pension payout funds are (a) private pension fund
administrators; (b) life insurance companies authorised under Art. 20(3)(a) of Law 237/2015 that do
not hold a pension-fund management authorisation; (c) investment management companies authorised
under Art. 9 of GEO 32/2012 that do not hold such an authorisation; (d) private pension payment
companies constituted as joint-stock companies with the exclusive object "Activităţi ale fondurilor
de pensii, cu excepţia celor din sistemul public de asigurări sociale". Art. 4(2): all of them must
obtain authorisation as a provider from ASF. Art. 4(3) adds cross-border IORPs and PEPP providers.

This is the widest provider definition of the four comparators: not just insurers, and not a
dedicated form only.

### 4.2 Payout types - CONFIRMED

Two fund types (Art. 3(1), points 21 and 22): a programmed-withdrawal payout fund and a life-annuity
payout fund ("fond de plată a pensiilor viagere"). For programmed withdrawal the monthly payment
equals the social indemnity for pensioners set for the public system, updated annually by the
provider (Art. 60(4)-(5)); by way of exception, if the personal asset would imply a payout period
longer than 8 years, the monthly pension may exceed that limit provided the total duration is at
least 8 years (Art. 60(6)).
Art. 55(1): the member may receive at most 30% of the personal asset transferred to the payout fund,
once, as a single payment before monthly pensions begin.

### 4.3 The mortality basis - CONFIRMED: a static national population table, and only as a definition

Art. 3(1)(41):

> "41. tabel biometric - instrument statistic publicat de Institutul National de Statistică i care
> furnizează informaţii cu privire la probabilităţile de supravieţuire i deces, în funcţie de
> vârstă;"

("biometric table - a statistical instrument published by the National Institute of Statistics which
provides information on survival and death probabilities by age")

Art. 3(1)(9):

> "9. anuitate - valoare actuarială prezentă a unei serii de plăţi unitare pe o perioadă, plătibilă
> cu titlu de pensie, uneia sau mai multor persoane, după caz, calculată pe baza probabilităţilor de
> supravieţuire ale respectivei/respectivelor persoane, a rentabilităţilor investiţionale viitoare
> estimate şi a valorii comisionului de administrare;"

("annuity - the present actuarial value of a series of unit payments over a period, payable as a
pension to one or more persons, calculated on the basis of the survival probabilities of that
person or those persons, the estimated future investment returns and the value of the administration
commission")

Two things are notable. First, the reference table is the **national statistical office's population
table**, with no annuitant adjustment and **no requirement of projection or improvement** anywhere in
the law. Second, the term "tabel biometric" appears in the definitions and **nowhere in an operative
article** - a full-text search of the promulgated law finds it once, plus "riscuri biometrice" in the
risk definitions (Art. 3(1)(37)) and in the risk-management duties (Art. 22-ish). The actuarial
function's duties are listed in Art. 28(1): calculating the life annuities, technical reserves, the
technical provision, the funding rate, "calculul procentului de indexare a pensiilor private
viagere" ("calculation of the indexation percentage for life annuities"), assessing the adequacy of
methodologies, models and assumptions, and "alte atribuţii stabilite prin reglementările A.S.F."
("other duties established by ASF regulations"). The actuarial basis is therefore left to ASF
secondary legislation, exactly the step North Macedonia has not taken.

### 4.4 Unisex pricing - NOT FOUND in the payout law

No provision on sex-based or gender-neutral pricing; the words "unisex" and "sex" do not appear.
EU law applies, but the payout law itself is silent.

### 4.5 Maximum interest rate or discount basis - NOT FOUND

No cap or prescribed discount basis in the law; the annuity definition refers to "rentabilităţilor
investiţionale viitoare estimate" (estimated future investment returns) without constraining them.
Left to ASF regulation.

### 4.6 Commission cap - CONFIRMED

Art. 37(1):

> "Pentru activitatea de administrare a fondului de plată, furnizorul percepe un comision lunar de
> administrare, din activul fondului de plată, care nu poate depăi 0,05 % din acesta."

("For the administration of the payout fund the provider charges a monthly administration commission
from the fund's assets, which may not exceed 0.05% thereof.")

A monthly 0.05% asset-based cap (of the order of 0.6% per year), with increases subject to prior ASF
approval and decreases to prior notification (Art. 37(4)) - an ongoing-charge cap rather than the
Macedonian up-front sales-commission cap.

### 4.7 Guarantee period, indexation, joint-life - partly CONFIRMED

A survivor component exists by design: Art. 3(1)(40) defines "supravieţuitor" as the person
designated by the member in the contract for a "pensie viageră cu componentă de supravieţuitor"
("life annuity with a survivor component"). Indexation of life annuities is contemplated but its
rule is not in the law (Art. 28(1)(e), above). For programmed withdrawal, Art. 60 provides
that the sum of payments to the member and heirs is at least the asset value net of legal
commissions, and unused amounts pass to heirs. A mandated guarantee period comparable to Slovakia's
84 months was **NOT FOUND**.

### 4.8 Entry into force, and the state of the market - CONFIRMED

Art. 113: "Prezenta lege intră în vigoare la un an de la data publicării în Monitorul Oficial al
României, Partea I." ("This law enters into force one year after its publication in the Official
Gazette of Romania, Part I.") With publication on 5 January 2026 (SECONDARY), that is **5 January
2027**. Take-up is therefore necessarily zero at the date of this note, and no provider can yet be
paying an annuity.

ASF began issuing the implementing framework during 2026: secondary reporting indicates *Norma ASF
nr. 16/2026* on the authorisation of private pension providers (Monitorul Oficial Part I no. 712 of
27 August 2026) and a norm on providers' share capital. Both are **SECONDARY**; the ASF website
was not accessible, so neither is cited as a source in the paper. The relevant, citable fact is the one in the law itself: Romania legislated
the payout phase eighteen years after the second pillar started, and delegated the actuarial basis
to the supervisor.

There is one further documented feature worth recording, from the legislative record itself: the law
went through re-examination after a Constitutional Court decision (the Senate record for L214/2025
lists "sesizarea Curţii Constituţionale", "decizia Curţii Constituţionale", "forma adoptată de Senat
- în urma reexaminării" and "forma trimisă la promulgare - după reexaminare"), i.e. the payout design
was constitutionally contested before it entered into force. The decision text (file 25L214DC1) was
not read - **NOT FOUND** as to its content.

---

## 5. Comparison table

| Item | Croatia | Slovakia | Latvia | Romania | North Macedonia (for contrast) |
|---|---|---|---|---|---|
| Payout phase operating since | 2014 regime; annuities paid | 2015 | 2003 option, reorganised 2019-2023 | Law in force 5.1.2027; nothing yet | No annuity ever paid |
| Who may pay the annuity | Dedicated pension insurance company (MOD), HANFA licence | Life insurer, NBS licence, via central offer system | Licensed life insurer, VSAA is contracting party | Pension fund administrator, life insurer, investment manager, or dedicated payout company - all ASF-authorised | Insurer with class-24 licence; none exists |
| Central quotation mechanism | Informative calculations by MODs; REGOS choice statement | Yes, statutory offer system at Sociálna poisťovňa; binding 30 days | VSAA sends list of insurers and calculators | Not established in the law | Law provides a quotation procedure; unused |
| Table prescribed by supervisor | No | No | No | No (only defines a national population table) | МАПАС bylaw prescribes rules for pension companies; no ASO standard |
| Projected (improvement-adjusted) basis | Yes - supervisor's documented practice | **Yes - required by statute, §46(3)** | Not required | Not required | ASO reserving rulebook requires correction for expected future mortality decreases; no Art. 22 joint standard |
| How improvement is expressed | Qualitative correction for expected lengthening of life over the payout period | Qualitative: "shall take into account future demographic development" | n/a | n/a | МАПАС: **ceiling** of up to +3 years of e_x |
| Ceiling on improvement allowance | None found | None found | n/a | n/a | Yes, +3 years |
| Annuitant-experience table | None; absence flagged as a problem by the ministry | Not prescribed; insurers' own data | Not prescribed | Not prescribed | Not available |
| Unisex required | Yes, ZMOD Art. 105 and 107 | Yes, age is the only rating factor, §46(3) | Not in the pension instruments; EU law applies | Not in the payout law | No - sex-specific tables required |
| Maximum interest / discount basis | No cap; expected long-run return, ex ante non-objection; acquisition costs ≤3.5% of transfer | No cap; guaranteed return registered and disclosed; ≥90% of surplus to the insured | No cap | No cap in the law | МАПАС caps the rate by reference to domestic 5y+ bond yields; ASO rulebook caps the reserving rate |
| Guarantee period | Optional form; beneficiary gets ≥50% | **Compulsory 84 months (7 years)** | Not prescribed | Not found | Law allows guarantee-period variants |
| Indexation | CPI indexation must be offered, at least twice a year; non-indexed only alongside indexed | Optional variant at a statutory 2% unless NBS sets otherwise | Not prescribed | Rule left to ASF | Not mandated |
| Joint-life / survivor | Four forms; ≥60% to surviving spouse; quasi-mandatory where spouse >50 and without income | Survivor pension at 100% for 1 or 2 years | Co-insured spouse optional | Survivor component defined | Joint-life variants allowed |
| Commission / expense cap | Acquisition costs ≤3.5% of transfer; no sales-commission cap found | **Financial intermediation prohibited** (§46f(16)); no surrender charge | Not prescribed | Monthly administration commission ≤0.05% of assets | Sales commission ≤2.5% of premium |
| Small-balance handling | Lump sum ≤20% if basic pension above minimum | Statutory fallback: no offer => drawdown ≤€14.90/month until exhausted | Below insurers' minimum => capital returns to the public pillar | Programmed withdrawal at the social indemnity level | Programmed withdrawal by the pension company |
| Annuity take-up | **35%** (4,188 of 11,875 choices, to 31.10.2024) | **22.7%** (2,588 of 11,416 payout decisions, 2025) | NOT FOUND (primary) | 0 by construction | 0% (all 147 payouts to 30.06.2026 are programmed withdrawals) |
| Providers in the market | 2 | NOT FOUND (primary) | NOT FOUND (primary) | 0 authorised yet | 0 |
| Average annuity | n/a (not extracted) | €26.20/month, 2025 | NOT FOUND | n/a | n/a |
| Documented post-launch problem | Falling share choosing both pillars; indexation obligation fed into lower quotes; no annuitant tables; a popular product form unregulated | 1,028 savers with no offer at all in 2025; very low amounts; selection by the reference-amount gate | Insurer-set minimum premium excludes small balances | Constitutional challenge before entry into force | No market at all |

---

## 6. What comparable supervisors require on mortality improvement, and how the Macedonian position compares

**Two of the four require or expect a forward-looking mortality basis, and the stronger of the two
does it in primary legislation.** Slovakia - the closest design analogue to what North Macedonia
legislated - writes it into the Act itself: the mortality probability used in pricing "zohľadňuje aj
budúci demografický vývoj" (§46(3)). Croatia achieves the same outcome through licensing and
ex ante price review, and its supervisor describes the resulting practice as population tables
"korigiraju ... za očekivano produljenja trajanja života tijekom razdoblja isplate mirovina". Latvia
prescribes nothing and leaves it to Solvency II; Romania's brand-new law mentions only a static
population table published by its statistical office, and delegates everything else to ASF norms.

**This makes the paper's recommendation regional practice, not an innovation - and that is the
stronger argument.** The recommendation should be framed as: ASO would be aligning with the Slovak
statutory standard and Croatian supervisory practice, and moving ahead of Latvia and Romania in
explicitness. It should *not* be framed as prescribing a specific table: none of the four
comparators prescribes one, and Croatia's own ministry working group shows why - even after a decade
of a live annuity market, no official annuitant table exists, and building one requires the
statistical office, the actuarial association, academia and the supervisor together. The defensible
recommendation is therefore a **requirement plus a review mechanism**: require a projected basis,
require the improvement assumption to be documented and justified with data, and review it ex ante
(Croatia's 30-day non-objection on unit amounts, Slovakia's registration of the guaranteed return
and the offer system, are the two working templates).

**On the МАПАС "+3 years" ceiling, the regional evidence is one-sided.** No comparator caps the
improvement allowance. Croatia and Slovakia impose an obligation to allow for improvement and leave
the size of the allowance to the actuary subject to supervision; Latvia and Romania impose nothing.
A ceiling of up to three years of e_x is a limit on prudence, which is the opposite direction of
travel from the two comparators that regulate the issue at all. The paper can say this plainly: the
Macedonian instrument is unusual in the region not because it mentions improvement - it does - but
because the only quantitative statement it makes about improvement is an upper bound. And the
Macedonian ceiling binds only the pension-company (programmed-withdrawal) side; on the insurer side,
where the annuity would actually be priced, there is no Art. 22 joint standard at all.

**Three further findings that bear on how the paper frames things.**

1. **Take-up.** Where it is measured, annuity take-up against a competing non-annuity route is 35%
   in Croatia and 22.7% in Slovakia, and in Slovakia that includes a regime in which the lifetime
   annuity is legally the default for everyone below the reference amount. RQ4's scenario grid of
   30% / 60% / 100% should be read with this in mind: 30% is the empirically plausible case, 60% is
   already above anything observed in the region, and 100% is a pure upper bound. This is a
   defensible, sourced justification for the scenario range and should be cited in the analysis
   rather than left as an arbitrary grid.
2. **The small-balance problem is the binding practical constraint, not adverse selection.** Both
   Slovakia and Latvia have explicit statutory machinery for the case where no insurer will quote
   because the accumulated capital is too small - in Slovakia 1,028 savers in a single year. With
   Macedonian second-pillar balances still immature, any recommendation that assumes annuities will
   simply be available once a licence is issued is vulnerable; the minimum-premium question belongs
   in the recommendations.
3. **Indexation is where the mortality basis and the price collide.** Croatia's mandatory CPI
   indexation is documented as having reduced quoted annuities enough to shift retirees away from
   the second pillar, and Slovakia sets the indexation rate at a statutory 2% rather than leaving it
   to the insurer. If the Macedonian recommendation touches indexation, this trade-off should be
   stated: a projected mortality basis and mandatory indexation both lower the starting annuity, and
   the two together can push retirees into programmed withdrawal.

### Caveats

- Croatia's projected basis is documented on the supervisor's consumer page and in the licensing and
  price-review provisions, not in a bylaw that quantifies it. It is CONFIRMED as supervisory
  description of practice, not as a prescribed numerical standard.
- The Croatian take-up ratio rests on a count of choice statements whose period is not stated in the
  source.
- The Slovak participating-insurer count, the Latvian take-up and provider list, and the Romanian
  gazette citation and ASF norms are NOT FOUND from primary sources. None of
  them is load-bearing for the argument in §6.
- Romania's article numbering is taken from the promulgated form in the Senate's legislative record;
  it should be checked against Monitorul Oficial before article numbers are cited.
