# Долгиот живот како ризик: ануитетите од вториот столб во Северна Македонија

Код, податоци и резултати за трудот „Долгиот живот како ризик: ануитетите од вториот столб во Северна Македонија“ (Скопје, септември 2026).

Трудот проектира смртност за возрастите над 60 години во Северна Македонија со стохастички модели (Ли-Картер, CBD, Реншо-Хаберман, APC), ги вреднува доживотните ануитети од вториот столб според периодна и кохортна таблица, го споредува шокот за долговечност од Солвентност II со модел-базирана вредност под ризик од 99,5% и ја проценува обврската на ниво на пензискиот систем за кохортите што се пензионираат во периодот 2026-2040.

## Содржина по папки

- `data/raw/` - изворни податоци, зачувани непроменети: МАКСТАТ (ДЗС), Евростат, МАПАС, АСО, НБРСМ, ЕИОПА, правни текстови на ЕУ и на споредбените земји. `data/raw/SOURCES.csv` е регистарот на потеклото: за секоја датотека се наведени институцијата, URL-адресата, датумот на пристап, опфатот и забелешки.
- `data/clean/` - матрици на умрени, изложеност и стапки на смртност по возраст и година, периодни таблици на смртност, проверки на квалитетот, валидација наспроти објавените таблици на ДЗС и ефектот од пописната ревизија.
- `scripts/fetch/` - преземање на изворните податоци (МАКСТАТ PX-Web, Евростат JSON-stat).
- `scripts/clean/` - изградба на матриците, затворање на таблицата на старите возрасти, валидација и слики за податоците.
- `analysis/mortality/` - приспособување, тестирање врз минати податоци и симулација на моделите на смртност (R) и проектирани таблици.
- `analysis/annuity/` - вреднување на ануитети, шок од Солвентност II наспроти VaR, маргина на ризик, тест на одржливост на законските форми на исплата.
- `analysis/system/` - обврска на ниво на вториот столб, модел на акумулација, избор на членот меѓу програмирано повлекување и ануитет.
- `analysis/compare/` - студија за споредбени земји: тестирање на истата постапка за проекција со скратување на серијата за Бугарија и Естонија (20 години) и регионален контекст 2003-2023 (податоци во `data/raw/compare/`).
- `research/` - правен преглед (`legal/`), институционален преглед и споредба на режимите за исплата во Хрватска, Словачка, Латвија и Романија (`institutional/`, документи во `data/raw/compare_legal/`), преглед на литературата и библиографија (`literature/refs.bib`).
- `results/*.json` - сите бројки што се наведуваат во трудот, по области (`data`, `mortality`, `annuity`, `system`, `legal`, `compare`, `compare_legal`, `data_availability`). Секоја вредност има соседен клуч `*_source` или `*_note` со изворот или методот.
- `figures/` - слики во PNG и SVG.

## Репродукција

Целиот тек, од изворните податоци до резултатите:

```
bash scripts/run_all.sh
```

Студијата за споредбените земји се извршува засебно:

```
python3 scripts/fetch/eurostat_compare.py
python3 analysis/compare/fit_compare.py
```

Семето е фиксирано на 2026 во сите стохастички чекори.

Датотеките `analysis/mortality/qx_sims_*.parquet` и `analysis/mortality/*.rds` (симулирани патеки и приспособени модели) не се вклучени поради големината; `run_all.sh` ги создава повторно.

## Околина

- R 4.4.3: StMoMo 0.4.1, demography 2.0.1, forecast 9.0.2, arrow 23.0.1.1, како и data.table, jsonlite, ggplot2, scales, svglite, dplyr.
- Python 3.11.5: pandas 2.3.1, numpy 2.2.1, pyarrow 23.0.1, scipy 1.16.3, matplotlib 3.10.5, openpyxl, xlrd, pillow, pyjstat (`pip install -r requirements.txt`).
- `pdftoppm` од poppler (за читање на графиконот 5.3 од годишниот извештај на МАПАС).

## Бројки во трудот

Секоја бројка во трудот доаѓа од `results/*.json`; клучот и неговиот извор (`*_source`) овозможуваат секоја вредност да се следи до податоците и постапката што ја дала.

## Податоци

Изворните податоци се од јавни извори (МАКСТАТ, Евростат, МАПАС, АСО, НБРСМ, ЕИОПА и службени гласила) и за нив важат условите на институциите што ги објавиле. Потеклото и датумот на пристап за секоја датотека се во `data/raw/SOURCES.csv`.

## English summary

Code, data and results for a paper (in Macedonian) on longevity risk and second-pillar life annuities in North Macedonia. The pipeline fits stochastic mortality models (Lee-Carter, CBD, Renshaw-Haberman, APC) to census-revised Macedonian data, values annuities on period and cohort tables, compares the Solvency II longevity shock with a model-based 99.5% VaR, and estimates the system-level liability for the cohorts retiring in 2026-2040. A comparator study backtests the same projection method on Bulgaria and Estonia, and an institutional comparison covers the payout regimes of Croatia, Slovakia, Latvia and Romania. Run `bash scripts/run_all.sh` to reproduce everything from `data/raw/` (seed 2026); the comparator study runs with `python3 analysis/compare/fit_compare.py`. Data provenance is listed in `data/raw/SOURCES.csv`. Every number in the paper comes from `results/*.json`, where each key carries its source.
