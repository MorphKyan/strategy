# China ETF Basket Screening

- Universe file: `C:\Users\MorphKyan\tm-strategy\configs\risk_parity_etf_universe.yaml`
- Generated at: `2026-04-09T16:50:13`

## Eligible ETFs
- `510050` 上证50ETF | bucket: `equity` | sleeve: `mega_cap_equity` | history: 2005-02-23 to 2026-04-09 (20.37 years)
- `510180` 上证180ETF | bucket: `equity` | sleeve: `large_cap_equity` | history: 2006-05-18 to 2026-04-09 (19.18 years)
- `510300` 沪深300ETF | bucket: `equity` | sleeve: `broad_equity` | history: 2012-05-28 to 2026-03-16 (13.30 years)
- `510310` 沪深300ETF易方达 | bucket: `equity` | sleeve: `broad_equity_alt` | history: 2013-03-25 to 2026-03-16 (12.50 years)
- `510500` 中证500ETF | bucket: `equity` | sleeve: `mid_cap_equity` | history: 2013-03-15 to 2026-04-09 (12.59 years)
- `510880` 红利ETF | bucket: `equity` | sleeve: `dividend_equity` | history: 2007-01-18 to 2026-04-07 (18.52 years)
- `512890` 红利低波ETF | bucket: `equity` | sleeve: `low_vol_equity` | history: 2019-01-18 to 2026-04-07 (6.93 years)
- `511260` 十年国债ETF | bucket: `bond` | sleeve: `government_bond` | history: 2017-08-24 to 2026-03-16 (8.23 years)
- `518880` 黄金ETF | bucket: `gold` | sleeve: `gold` | history: 2013-07-29 to 2026-03-16 (12.18 years)

## Rejected For Short History
- `511130` 30年国债ETF | history: 2024-03-28 to 2026-03-16 (1.88 years)

## Top Candidate Baskets
### 1. 510880 红利ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.8427`
- Buckets: 510880->equity/dividend_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2017-08-24` to `2026-04-07` (8.29 years)
- Average absolute correlation: `0.1145`
- Inverse-vol concentration HHI: `0.5512`
- Average inverse-vol weights: `510880:0.156, 511260:0.714, 518880:0.130`
### 2. 510050 上证50ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.8352`
- Buckets: 510050->equity/mega_cap_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2017-08-24` to `2026-04-09` (8.30 years)
- Average absolute correlation: `0.1222`
- Inverse-vol concentration HHI: `0.5808`
- Average inverse-vol weights: `510050:0.126, 511260:0.740, 518880:0.135`
### 3. 510180 上证180ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.8328`
- Buckets: 510180->equity/large_cap_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2017-08-24` to `2026-04-09` (8.30 years)
- Average absolute correlation: `0.1314`
- Inverse-vol concentration HHI: `0.5813`
- Average inverse-vol weights: `510180:0.125, 511260:0.740, 518880:0.135`
### 4. 510300 沪深300ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.8294`
- Buckets: 510300->equity/broad_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2017-08-24` to `2026-03-16` (8.23 years)
- Average absolute correlation: `0.1270`
- Inverse-vol concentration HHI: `0.5902`
- Average inverse-vol weights: `510300:0.117, 511260:0.747, 518880:0.136`
### 5. 510500 中证500ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.8270`
- Buckets: 510500->equity/mid_cap_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2017-08-24` to `2026-04-09` (8.30 years)
- Average absolute correlation: `0.1280`
- Inverse-vol concentration HHI: `0.6147`
- Average inverse-vol weights: `510500:0.095, 511260:0.766, 518880:0.139`

## Generated Configs
- `C:\Users\MorphKyan\tm-strategy\configs\generated\risk_parity_basket_510880_511260_518880.yaml`
- `C:\Users\MorphKyan\tm-strategy\configs\generated\risk_parity_basket_510050_511260_518880.yaml`
- `C:\Users\MorphKyan\tm-strategy\configs\generated\risk_parity_basket_510180_511260_518880.yaml`
- `C:\Users\MorphKyan\tm-strategy\configs\generated\risk_parity_basket_510300_511260_518880.yaml`
- `C:\Users\MorphKyan\tm-strategy\configs\generated\risk_parity_basket_510500_511260_518880.yaml`
