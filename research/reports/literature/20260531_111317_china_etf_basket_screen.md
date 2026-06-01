# China ETF Basket Screening

- Universe file: `D:\strategy\research\configs\risk_parity_etf_universe.yaml`
- Generated at: `2026-05-31T11:13:17`

## Eligible ETFs
- `510050` 上证50ETF | bucket: `equity` | sleeve: `mega_cap_equity` | history: 2005-02-23 to 2026-04-09 (20.37 years)
- `510180` 上证180ETF | bucket: `equity` | sleeve: `large_cap_equity` | history: 2006-05-18 to 2026-04-09 (19.18 years)
- `510300` 沪深300ETF | bucket: `equity` | sleeve: `broad_equity` | history: 2012-05-28 to 2026-05-19 (13.47 years)
- `510310` 沪深300ETF易方达 | bucket: `equity` | sleeve: `broad_equity_alt` | history: 2013-03-25 to 2026-03-16 (12.50 years)
- `510500` 中证500ETF | bucket: `equity` | sleeve: `mid_cap_equity` | history: 2013-03-15 to 2026-04-09 (12.59 years)
- `510880` 红利ETF | bucket: `equity` | sleeve: `dividend_equity` | history: 2007-01-18 to 2026-04-07 (18.52 years)
- `512890` 红利低波ETF | bucket: `equity` | sleeve: `low_vol_equity` | history: 2019-01-18 to 2026-04-07 (6.93 years)
- `511260` 十年国债ETF | bucket: `bond` | sleeve: `government_bond` | history: 2017-08-24 to 2026-05-19 (8.39 years)
- `518880` 黄金ETF | bucket: `gold` | sleeve: `gold` | history: 2013-07-29 to 2026-05-19 (12.35 years)

## Rejected For Short History
- `511130` 30年国债ETF | history: 2024-03-28 to 2026-03-16 (1.88 years)

## Top Candidate Baskets
### 1. 510880 红利ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.8421`
- Buckets: 510880->equity/dividend_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2017-08-24` to `2026-04-07` (8.29 years)
- Average absolute correlation: `0.1128`
- Inverse-vol concentration HHI: `0.5556`
- Average inverse-vol weights: `510880:0.157, 511260:0.718, 518880:0.125`
### 2. 510300 沪深300ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.8333`
- Buckets: 510300->equity/broad_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2017-08-24` to `2026-05-19` (8.39 years)
- Average absolute correlation: `0.1323`
- Inverse-vol concentration HHI: `0.5970`
- Average inverse-vol weights: `510300:0.117, 511260:0.753, 518880:0.130`
### 3. 510050 上证50ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.8329`
- Buckets: 510050->equity/mega_cap_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2017-08-24` to `2026-04-09` (8.29 years)
- Average absolute correlation: `0.1267`
- Inverse-vol concentration HHI: `0.5860`
- Average inverse-vol weights: `510050:0.127, 511260:0.744, 518880:0.129`
### 4. 510180 上证180ETF, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.8302`
- Buckets: 510180->equity/large_cap_equity, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2017-08-24` to `2026-04-09` (8.29 years)
- Average absolute correlation: `0.1371`
- Inverse-vol concentration HHI: `0.5865`
- Average inverse-vol weights: `510180:0.127, 511260:0.744, 518880:0.129`
### 5. 510310 沪深300ETF易方达, 511260 十年国债ETF, 518880 黄金ETF
- Score: `0.8265`
- Buckets: 510310->equity/broad_equity_alt, 511260->bond/government_bond, 518880->gold/gold
- Common history: `2017-08-24` to `2026-03-16` (8.23 years)
- Average absolute correlation: `0.1303`
- Inverse-vol concentration HHI: `0.5998`
- Average inverse-vol weights: `510310:0.108, 511260:0.754, 518880:0.137`

## Generated Configs
- `D:\strategy\research\configs\generated\risk_parity_basket_510880_511260_518880.yaml`
- `D:\strategy\research\configs\generated\risk_parity_basket_510300_511260_518880.yaml`
- `D:\strategy\research\configs\generated\risk_parity_basket_510050_511260_518880.yaml`
- `D:\strategy\research\configs\generated\risk_parity_basket_510180_511260_518880.yaml`
- `D:\strategy\research\configs\generated\risk_parity_basket_510310_511260_518880.yaml`
