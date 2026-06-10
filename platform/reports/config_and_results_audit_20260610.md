# 配置与结果目录审计清单

生成日期：2026-06-10

## baseline_opt 配置三年训练样本检查

判定口径：组合共同训练样本为最早共同有行情日期至 `2025-06-30`，必须严格大于三年。

| 配置 | 代码 | 共同起点 | 训练截止 | 年数 | 结论 |
|---|---|---:|---:|---:|---|
| `baseline_opt_mvp_equal_weight_risk_parity_ewma.yaml` | `510300,518880,511260` | 2017-08-24 | 2025-06-30 | 7.849 | 通过 |
| `baseline_opt_r1_domestic_ewma_risk_parity_cvar_dynamic_budget.yaml` | `510300,512890,518880,511260` | 2019-01-18 | 2025-06-30 | 6.448 | 通过 |
| `baseline_opt_r1_domestic_rolling_risk_parity_cvar_dynamic_budget.yaml` | `510300,512890,518880,511260` | 2019-01-18 | 2025-06-30 | 6.448 | 通过 |
| `baseline_opt_r2_global_dividend_ewma_risk_parity_cvar_dynamic_budget.yaml` | `512890,513500,518880,511260` | 2019-01-18 | 2025-06-30 | 6.448 | 通过 |
| `baseline_opt_r2_global_ewma_risk_parity_cvar_dynamic_budget.yaml` | `510300,512890,513500,518880,511260` | 2019-01-18 | 2025-06-30 | 6.448 | 通过 |
| `baseline_opt_r3_global_nasdaq_all_weather_ewma_risk_parity_cvar_dynamic_budget.yaml` | `510300,512890,513100,518880,511260,159985,159981` | 2020-01-17 | 2025-06-30 | 5.451 | 通过 |
| `baseline_opt_r5_cvar_dynamic_budget_risk_parity_ewma.yaml` | `510300,518880,511260` | 2017-08-24 | 2025-06-30 | 7.849 | 通过 |
| `baseline_opt_r6_adaptive_risk_deviation_risk_parity_ewma.yaml` | `510300,518880,511260` | 2017-08-24 | 2025-06-30 | 7.849 | 通过 |
| `baseline_opt_risk_parity_gerber_risk_parity_lw_cov.yaml` | `510300,518880,511260` | 2017-08-24 | 2025-06-30 | 7.849 | 通过 |
| `baseline_opt_risk_parity_hrp_risk_parity_ewma.yaml` | `510300,518880,511260` | 2017-08-24 | 2025-06-30 | 7.849 | 通过 |
| `baseline_opt_risk_parity_lw_cov_risk_parity_ewma.yaml` | `510300,518880,511260` | 2017-08-24 | 2025-06-30 | 7.849 | 通过 |
| `baseline_opt_us_blend_ewma_risk_parity_cvar_dynamic_budget.yaml` | `510300,512890,513500,513100,518880,511260` | 2019-01-18 | 2025-06-30 | 6.448 | 通过 |

不合规 `baseline_opt_*` 配置数量：0。

## candidate.oos_metrics_available=false 清单

已删除 102 个 `candidate_config` 缺失或已不存在、且仅残留在 `reports/metrics.json` 中的旧报告目录。以下为删除后仍保留的 `oos_metrics_available=false` 项；保留原因是其 `candidate_config` 当前仍可定位到。

| metrics.json | experiment | candidate_config |
|---|---|---|
| `platform\reports\experiments\baseline_m3m4_fundamental_exp_semi_cov\20260604_144704\metrics.json` | `baseline_m3m4_fundamental_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_m3m4_fundamental_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_m3m4_fundamental_exp_semi_cov\20260604_144925\metrics.json` | `baseline_m3m4_fundamental_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_m3m4_fundamental_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_mvp_equal_weight_exp_semi_cov\20260604_144703\metrics.json` | `baseline_mvp_equal_weight_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_mvp_equal_weight_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_mvp_equal_weight_exp_semi_cov\20260604_144922\metrics.json` | `baseline_mvp_equal_weight_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_mvp_equal_weight_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_r1_domestic_ewma_exp_semi_cov\20260604_144706\metrics.json` | `baseline_r1_domestic_ewma_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r1_domestic_ewma_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_r1_domestic_ewma_exp_semi_cov\20260604_145427\metrics.json` | `baseline_r1_domestic_ewma_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r1_domestic_ewma_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_r1_domestic_ewma_exp_semi_cov\20260604_145729\metrics.json` | `baseline_r1_domestic_ewma_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r1_domestic_ewma_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_r1_domestic_low_vol_ewma_exp_semi_cov\20260604_144707\metrics.json` | `baseline_r1_domestic_low_vol_ewma_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r1_domestic_low_vol_ewma_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_r1_domestic_low_vol_ewma_exp_semi_cov\20260604_145840\metrics.json` | `baseline_r1_domestic_low_vol_ewma_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r1_domestic_low_vol_ewma_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_r1_domestic_rolling_exp_semi_cov\20260604_144705\metrics.json` | `baseline_r1_domestic_rolling_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r1_domestic_rolling_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_r1_domestic_rolling_exp_semi_cov\20260604_144927\metrics.json` | `baseline_r1_domestic_rolling_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r1_domestic_rolling_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_r2_global_dividend_ewma_exp_semi_cov\20260604_144709\metrics.json` | `baseline_r2_global_dividend_ewma_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r2_global_dividend_ewma_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_r2_global_dividend_ewma_exp_semi_cov\20260604_150057\metrics.json` | `baseline_r2_global_dividend_ewma_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r2_global_dividend_ewma_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_r2_global_ewma_exp_semi_cov\20260604_144708\metrics.json` | `baseline_r2_global_ewma_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r2_global_ewma_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_r2_global_ewma_exp_semi_cov\20260604_145948\metrics.json` | `baseline_r2_global_ewma_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r2_global_ewma_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_r3_global_nasdaq_all_weather_ewma_exp_semi_cov\20260604_144710\metrics.json` | `baseline_r3_global_nasdaq_all_weather_ewma_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r3_global_nasdaq_all_weather_ewma_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_r3_global_nasdaq_all_weather_ewma_exp_semi_cov\20260604_150202\metrics.json` | `baseline_r3_global_nasdaq_all_weather_ewma_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_r3_global_nasdaq_all_weather_ewma_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_risk_parity_hrp_exp_semi_cov\20260604_144712\metrics.json` | `baseline_risk_parity_hrp_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_risk_parity_hrp_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_risk_parity_hrp_exp_semi_cov\20260604_150343\metrics.json` | `baseline_risk_parity_hrp_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_risk_parity_hrp_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_risk_parity_lw_cov_exp_semi_cov\20260604_144713\metrics.json` | `baseline_risk_parity_lw_cov_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_risk_parity_lw_cov_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_risk_parity_lw_cov_exp_semi_cov\20260604_150346\metrics.json` | `baseline_risk_parity_lw_cov_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_risk_parity_lw_cov_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_us_blend_ewma_exp_semi_cov\20260604_144711\metrics.json` | `baseline_us_blend_ewma_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_us_blend_ewma_candidate_semi_cov.yaml` |
| `platform\reports\experiments\baseline_us_blend_ewma_exp_semi_cov\20260604_150238\metrics.json` | `baseline_us_blend_ewma_exp_semi_cov` | `C:\Users\morph\.gemini\antigravity-cli\brain\0b91284b-6f95-49a8-9bc5-f0f112a0ce57\.system_generated\worktrees\subagent-Quant-Researcher-1--R011--quant-researcher-66d2a2f5\platform\configs\generated\baseline_us_blend_ewma_candidate_semi_cov.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612\20260531_001018\metrics.json` | `etf_selection_20260531_000612` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510300_159980_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612\20260531_001053\metrics.json` | `etf_selection_20260531_000612` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510300_159980_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612\20260531_001129\metrics.json` | `etf_selection_20260531_000612` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510300_159980_159985_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612\20260531_001205\metrics.json` | `etf_selection_20260531_000612` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510300_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612\20260531_001241\metrics.json` | `etf_selection_20260531_000612` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510310_159980_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612\20260531_001317\metrics.json` | `etf_selection_20260531_000612` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510310_159980_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612\20260531_001353\metrics.json` | `etf_selection_20260531_000612` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510310_159980_159985_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612\20260531_001428\metrics.json` | `etf_selection_20260531_000612` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510310_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_aligned\20260531_001557\metrics.json` | `etf_selection_20260531_000612_aligned` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510300_159980_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_aligned\20260531_001619\metrics.json` | `etf_selection_20260531_000612_aligned` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510300_159980_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_aligned\20260531_001641\metrics.json` | `etf_selection_20260531_000612_aligned` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510300_159980_159985_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_aligned\20260531_001705\metrics.json` | `etf_selection_20260531_000612_aligned` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510300_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_aligned\20260531_001728\metrics.json` | `etf_selection_20260531_000612_aligned` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510310_159980_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_aligned\20260531_001751\metrics.json` | `etf_selection_20260531_000612_aligned` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510310_159980_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_aligned\20260531_001814\metrics.json` | `etf_selection_20260531_000612_aligned` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510310_159980_159985_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_aligned\20260531_001837\metrics.json` | `etf_selection_20260531_000612_aligned` | `D:\strategy\etf_selection\generated_configs\20260531_000612\platform_basket_518880_510310_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt\20260531_004408\metrics.json` | `etf_selection_20260531_000612_execopt` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510300_159980_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt\20260531_004430\metrics.json` | `etf_selection_20260531_000612_execopt` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510300_159980_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt\20260531_004453\metrics.json` | `etf_selection_20260531_000612_execopt` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510300_159980_159985_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt\20260531_004517\metrics.json` | `etf_selection_20260531_000612_execopt` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510300_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt\20260531_004540\metrics.json` | `etf_selection_20260531_000612_execopt` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510310_159980_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt\20260531_004603\metrics.json` | `etf_selection_20260531_000612_execopt` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510310_159980_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt\20260531_004626\metrics.json` | `etf_selection_20260531_000612_execopt` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510310_159980_159985_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt\20260531_004649\metrics.json` | `etf_selection_20260531_000612_execopt` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510310_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt_v2\20260531_004857\metrics.json` | `etf_selection_20260531_000612_execopt_v2` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510300_159980_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt_v2\20260531_004919\metrics.json` | `etf_selection_20260531_000612_execopt_v2` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510300_159980_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt_v2\20260531_004941\metrics.json` | `etf_selection_20260531_000612_execopt_v2` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510300_159980_159985_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt_v2\20260531_005004\metrics.json` | `etf_selection_20260531_000612_execopt_v2` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510300_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt_v2\20260531_005025\metrics.json` | `etf_selection_20260531_000612_execopt_v2` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510310_159980_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt_v2\20260531_005047\metrics.json` | `etf_selection_20260531_000612_execopt_v2` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510310_159980_159985_159981_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt_v2\20260531_005109\metrics.json` | `etf_selection_20260531_000612_execopt_v2` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510310_159980_159985_511260.yaml` |
| `platform\reports\experiments\etf_selection_20260531_000612_execopt_v2\20260531_005130\metrics.json` | `etf_selection_20260531_000612_execopt_v2` | `D:\strategy\etf_selection\generated_configs\20260531_000612\optimized_execution\platform_basket_518880_510310_159985_159981_511260.yaml` |
| `platform\reports\experiments\fundamental_value_equal_weight\20260602_235135\metrics.json` | `fundamental_value_equal_weight` | `configs\generated\platform_research_dividend_fundamental.yaml` |
| `platform\reports\experiments\fundamental_value_equal_weight\20260602_235156\metrics.json` | `fundamental_value_equal_weight` | `configs\generated\platform_research_global_fundamental.yaml` |
| `platform\reports\experiments\fundamental_value_equal_weight\20260602_235237\metrics.json` | `fundamental_value_equal_weight` | `configs\generated\platform_research_baseline_fundamental.yaml` |
| `platform\reports\experiments\fundamental_value_equal_weight\20260602_235239\metrics.json` | `fundamental_value_equal_weight` | `configs\generated\platform_research_dividend_fundamental.yaml` |
| `platform\reports\experiments\fundamental_value_equal_weight\20260602_235301\metrics.json` | `fundamental_value_equal_weight` | `configs\generated\platform_research_global_fundamental.yaml` |
| `platform\reports\experiments\fundamental_value_equal_weight\20260602_235443\metrics.json` | `fundamental_value_equal_weight` | `configs\generated\platform_research_baseline_fundamental.yaml` |
| `platform\reports\experiments\fundamental_value_equal_weight\20260602_235505\metrics.json` | `fundamental_value_equal_weight` | `configs\generated\platform_research_dividend_fundamental.yaml` |
| `platform\reports\experiments\fundamental_value_equal_weight\20260602_235528\metrics.json` | `fundamental_value_equal_weight` | `configs\generated\platform_research_global_fundamental.yaml` |
| `platform\reports\experiments\risk_parity_ewma_dd_recovery\20260602_161703\metrics.json` | `risk_parity_ewma_dd_recovery` | `D:\strategy\platform\configs\generated\platform_overseas_us_blend_ewma_dd_rec.yaml` |
| `platform\reports\experiments\style_cross_market_dividend_low_vol_core\20260531_012608\metrics.json` | `style_cross_market_dividend_low_vol_core` | `C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\platform_dividend_low_vol_core.yaml` |
| `platform\reports\experiments\style_cross_market_dividend_replace_hs300\20260531_012443\metrics.json` | `style_cross_market_dividend_replace_hs300` | `C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\platform_dividend_replace_hs300.yaml` |
| `platform\reports\experiments\style_cross_market_hk_cross_market\20260531_012647\metrics.json` | `style_cross_market_hk_cross_market` | `C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\platform_hk_cross_market.yaml` |
| `platform\reports\experiments\style_cross_market_low_vol_replace_hs300\20260531_012529\metrics.json` | `style_cross_market_low_vol_replace_hs300` | `C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\platform_low_vol_replace_hs300.yaml` |
| `platform\reports\experiments\style_cross_market_refine_add_dividend_to_baseline\20260531_013158\metrics.json` | `style_cross_market_refine_add_dividend_to_baseline` | `C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_013145_style_cross_market_refine_platform\platform_refine_add_dividend_to_baseline.yaml` |
| `platform\reports\experiments\style_cross_market_refine_dividend_dax\20260531_013417\metrics.json` | `style_cross_market_refine_dividend_dax` | `C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_013145_style_cross_market_refine_platform\platform_refine_dividend_dax.yaml` |
| `platform\reports\experiments\style_cross_market_refine_dividend_nasdaq\20260531_013330\metrics.json` | `style_cross_market_refine_dividend_nasdaq` | `C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_013145_style_cross_market_refine_platform\platform_refine_dividend_nasdaq.yaml` |
| `platform\reports\experiments\style_cross_market_refine_dividend_sp500\20260531_013244\metrics.json` | `style_cross_market_refine_dividend_sp500` | `C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_013145_style_cross_market_refine_platform\platform_refine_dividend_sp500.yaml` |
| `platform\reports\experiments\style_cross_market_style_global_mix\20260531_012818\metrics.json` | `style_cross_market_style_global_mix` | `C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\platform_style_global_mix.yaml` |
| `platform\reports\experiments\style_cross_market_us_cross_market\20260531_012732\metrics.json` | `style_cross_market_us_cross_market` | `C:\Users\morph\.codex\worktrees\b6cc\strategy\etf_selection\generated_configs\20260531_012414_style_cross_market_platform\platform_us_cross_market.yaml` |

剩余数量：74。

## platform/results 目录用途

`platform/results/` 是平台原始运行产物目录，和 `platform/reports/` 的决策报告不同。这里通常保存可复核的 NAV、持仓、订单、成交、manifest、缓存、矩阵汇总和临时回测结果。

| 名称 | 类型 | 大小 | 更新时间 | 用途判断 |
|---|---|---:|---:|---|
| `all_configs_evaluation_results.json` | 文件 | 43080 | 2026-06-07 11:39:50 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `all_configs_user_holdings_results.json` | 文件 | 81798 | 2026-06-08 23:50:06 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `backtest_cache` | 目录 | - | 2026-06-07 00:08:40 | 共享回测缓存目录。 |
| `backtest_matrix_results.json` | 文件 | 50889 | 2026-06-07 11:09:57 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `backtests` | 目录 | - | 2026-06-07 11:39:50 | 标准/直接回测的原始 run 目录，通常包含 nav、positions、orders、trades。 |
| `backtests_temp` | 目录 | - | 2026-06-08 23:50:06 | 用户持仓/临时分析的原始回测结果目录。 |
| `cvar_dynamic_budget_comparison.json` | 文件 | 9447 | 2026-06-04 15:09:59 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `cvar_experiment_comparison.json` | 文件 | 6641 | 2026-06-03 23:20:10 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `experiment_comparison.json` | 文件 | 3985 | 2026-06-03 13:11:02 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `matrix_backtests_results.json` | 文件 | 13894 | 2026-06-05 08:13:13 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `optimal_strategy_mapping.json` | 文件 | 649 | 2026-06-07 11:09:57 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `platform` | 目录 | - | 2026-05-19 15:43:49 | 平台运行产物。 |
| `platform_classification_map.json` | 文件 | 7697 | 2026-06-01 15:15:40 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `platform_opt_summary.json` | 文件 | 9061 | 2026-06-01 15:07:27 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `platform_overseas_summary.json` | 文件 | 4053 | 2026-05-31 14:22:39 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `platform_portfolio_combinations_comparison.csv` | 文件 | 1688 | 2026-06-01 14:04:11 | 组合比较或表格结果。 |
| `platform_research_summary.json` | 文件 | 8820 | 2026-05-31 14:18:11 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `r006_experiment_summary.json` | 文件 | 69132 | 2026-06-04 11:21:25 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `r007_experiment_summary.json` | 文件 | 79053 | 2026-06-04 11:26:16 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `r011_experiments_summary.json` | 文件 | 86917 | 2026-06-04 15:11:52 | 脚本汇总结果或矩阵/实验汇总 JSON。 |
| `sensitivity_raw` | 目录 | - | 2026-06-02 15:16:23 | 起点敏感性测试原始 run。 |
| `sim_portfolios` | 目录 | - | 2026-06-08 20:54:46 | 模拟组合/checkpoint 相关结果。 |
| `summary_table.md` | 文件 | 9626 | 2026-06-07 11:39:54 | 结果汇总表。 |
| `temp_sensitivity_screen` | 目录 | - | 2026-06-07 10:31:44 | 平台运行产物。 |
| `verify_temp` | 目录 | - | 2026-06-02 15:16:09 | 验证过程产生的临时原始结果，仍可能含可复核交易产物。 |

