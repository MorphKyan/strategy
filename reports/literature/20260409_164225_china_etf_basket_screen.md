# China ETF Basket Screening

- Universe file: `C:\Users\MorphKyan\tm-strategy\configs\risk_parity_etf_universe.yaml`
- Generated at: `2026-04-09T16:42:25`

## Eligible ETFs
- `510300` 沪深300ETF | bucket: `equity` | sleeve: `broad_equity` | history: 2012-05-28 to 2026-03-16 (13.30 years)
- `510880` 红利ETF | bucket: `equity` | sleeve: `dividend_equity` | history: 2007-01-18 to 2026-04-07 (18.52 years)
- `512890` 红利低波ETF | bucket: `equity` | sleeve: `low_vol_equity` | history: 2019-01-18 to 2026-04-07 (6.93 years)
- `511260` 十年国债ETF | bucket: `bond` | sleeve: `government_bond` | history: 2017-08-24 to 2026-03-16 (8.23 years)
- `518880` 黄金ETF | bucket: `gold` | sleeve: `gold` | history: 2013-07-29 to 2026-03-16 (12.18 years)

## Top Candidate Baskets
### 1. 510880 红利ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.8427`
- Buckets: 510880->equity/dividend_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2017-08-24` to `2026-04-07` (8.29 years)
- Average absolute correlation: `0.1145`
- Inverse-vol concentration HHI: `0.5512`
- Average inverse-vol weights: `510880:0.156, 511260:0.714, 518880:0.130`
### 2. 510300 沪深300ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.8294`
- Buckets: 510300->equity/broad_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2017-08-24` to `2026-03-16` (8.23 years)
- Average absolute correlation: `0.1270`
- Inverse-vol concentration HHI: `0.5902`
- Average inverse-vol weights: `510300:0.117, 511260:0.747, 518880:0.136`
### 3. 510300 沪深300ETF, 510880 红利ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.7973`
- Buckets: 510300->equity/broad_equity, 510880->equity/dividend_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2017-08-24` to `2026-04-07` (8.29 years)
- Average absolute correlation: `0.2226`
- Inverse-vol concentration HHI: `0.4560`
- Average inverse-vol weights: `510300:0.101, 510880:0.140, 511260:0.642, 518880:0.117`
### 4. 512890 红利低波ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.7756`
- Buckets: 512890->equity/low_vol_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2019-01-18` to `2026-04-07` (6.93 years)
- Average absolute correlation: `0.1141`
- Inverse-vol concentration HHI: `0.6160`
- Average inverse-vol weights: `512890:0.112, 511260:0.767, 518880:0.120`
### 5. 510300 沪深300ETF, 512890 红利低波ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.7328`
- Buckets: 510300->equity/broad_equity, 512890->equity/low_vol_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2019-01-18` to `2026-04-07` (6.93 years)
- Average absolute correlation: `0.2219`
- Inverse-vol concentration HHI: `0.5076`
- Average inverse-vol weights: `510300:0.101, 512890:0.101, 511260:0.689, 518880:0.108`

## Generated Configs
- `C:\Users\MorphKyan\tm-strategy\configs\generated\risk_parity_basket_1_510880_511260_518880.yaml`
- `C:\Users\MorphKyan\tm-strategy\configs\generated\risk_parity_basket_2_510300_511260_518880.yaml`
- `C:\Users\MorphKyan\tm-strategy\configs\generated\risk_parity_basket_3_510300_510880_511260_518880.yaml`
- `C:\Users\MorphKyan\tm-strategy\configs\generated\risk_parity_basket_4_512890_511260_518880.yaml`
- `C:\Users\MorphKyan\tm-strategy\configs\generated\risk_parity_basket_5_510300_512890_511260_518880.yaml`
