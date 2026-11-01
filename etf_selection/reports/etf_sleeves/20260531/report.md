# ETF 袖子筛选报告

## 硬性规则
- 本流程按袖子独立筛选 ETF，再构建跨袖子候选篮子。
- 历史长度是硬性限制，默认至少 3 年。
- 商品袖子优先使用宽基商品 ETF；如果没有合格宽基商品 ETF，可以使用多个单商品 ETF。

## 袖子内排名
### bond
- `511260` 十年国债ETF | score=0.9579 | history=8.39y | peer_corr=1.0000 | eligible
- `511130` 30年国债ETF | score=0.0000 | history=1.88y | peer_corr=0.0000 | rejected: history_years<3.0
### commodity
- `159980` 有色期货ETF | score=0.4426 | history=3.94y | peer_corr=0.2686 | eligible
- `159985` 豆粕ETF | score=0.4387 | history=3.94y | peer_corr=0.2014 | eligible
- `159981` 能源化工ETF | score=0.4301 | history=3.94y | peer_corr=0.2975 | eligible
### gold
- `518880` 黄金ETF | score=1.0000 | history=12.35y | peer_corr=1.0000 | eligible
### hs300
- `510300` 沪深300ETF | score=0.9862 | history=13.47y | peer_corr=0.9635 | eligible
- `510310` 沪深300ETF易方达 | score=0.9751 | history=12.50y | peer_corr=0.9635 | eligible
### qdii
- `159920` 恒生ETF | score=0.8454 | history=13.08y | cost=0.0221 | premium_std=0.0070 | eligible
- `513500` 标普500ETF | score=0.6901 | history=11.89y | cost=0.0091 | premium_std=0.0243 | eligible
- `513100` 纳指100ETF | score=0.6691 | history=12.54y | cost=0.0119 | premium_std=0.0359 | eligible
- `513030` 德国DAXETF | score=0.2817 | history=11.26y | cost=0.0368 | premium_std=0.0184 | eligible

## 候选篮子
- `basket_8` 518880,510300,159985,159981,511260,513500 | score=0.6845 | corr=0.1188 | hhi=0.4227
- `basket_9` 518880,510300,159985,159981,511260,513100 | score=0.6825 | corr=0.1194 | hhi=0.4322
- `basket_11` 518880,510300,159980,159985,159981,511260,513500 | score=0.6771 | corr=0.1768 | hhi=0.3693
- `basket_12` 518880,510300,159980,159985,159981,511260,513100 | score=0.6756 | corr=0.1771 | hhi=0.3769
- `basket_20` 518880,510310,159985,159981,511260,513500 | score=0.6742 | corr=0.1353 | hhi=0.4202
- `basket_21` 518880,510310,159985,159981,511260,513100 | score=0.6723 | corr=0.1356 | hhi=0.4293
- `basket_2` 518880,510300,159980,159985,511260,513500 | score=0.6701 | corr=0.1746 | hhi=0.4109
- `basket_3` 518880,510300,159980,159985,511260,513100 | score=0.6677 | corr=0.1767 | hhi=0.4199
- `basket_23` 518880,510310,159980,159985,159981,511260,513500 | score=0.6674 | corr=0.1914 | hhi=0.3667
- `basket_14` 518880,510310,159980,159985,511260,513500 | score=0.6666 | corr=0.1663 | hhi=0.4114
- `basket_24` 518880,510310,159980,159985,159981,511260,513100 | score=0.6660 | corr=0.1915 | hhi=0.3740
- `basket_7` 518880,510300,159985,159981,511260,159920 | score=0.6659 | corr=0.1755 | hhi=0.4306
- `basket_15` 518880,510310,159980,159985,511260,513100 | score=0.6644 | corr=0.1683 | hhi=0.4202
- `basket_10` 518880,510300,159980,159985,159981,511260,159920 | score=0.6623 | corr=0.2221 | hhi=0.3757
- `basket_5` 518880,510300,159980,159981,511260,513500 | score=0.6584 | corr=0.2078 | hhi=0.4194
- `basket_6` 518880,510300,159980,159981,511260,513100 | score=0.6557 | corr=0.2109 | hhi=0.4287
- `basket_19` 518880,510310,159985,159981,511260,159920 | score=0.6549 | corr=0.1940 | hhi=0.4286
- `basket_22` 518880,510310,159980,159985,159981,511260,159920 | score=0.6520 | corr=0.2385 | hhi=0.3734
- `basket_1` 518880,510300,159980,159985,511260,159920 | score=0.6514 | corr=0.2320 | hhi=0.4185
- `basket_17` 518880,510310,159980,159981,511260,513500 | score=0.6477 | corr=0.2256 | hhi=0.4169

## 生成的平台配置
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510300_159985_159981_511260_513500.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510300_159985_159981_511260_513100.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510300_159980_159985_159981_511260_513500.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510300_159980_159985_159981_511260_513100.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510310_159985_159981_511260_513500.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510310_159985_159981_511260_513100.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510300_159980_159985_511260_513500.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510300_159980_159985_511260_513100.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510310_159980_159985_159981_511260_513500.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510310_159980_159985_511260_513500.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510310_159980_159985_159981_511260_513100.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510300_159985_159981_511260_159920.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510310_159980_159985_511260_513100.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510300_159980_159985_159981_511260_159920.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510300_159980_159981_511260_513500.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510300_159980_159981_511260_513100.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510310_159985_159981_511260_159920.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510310_159980_159985_159981_511260_159920.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510300_159980_159985_511260_159920.yaml`
- `D:\strategy\etf_selection\generated_configs\20260531_231347\platform_basket_518880_510310_159980_159981_511260_513500.yaml`
