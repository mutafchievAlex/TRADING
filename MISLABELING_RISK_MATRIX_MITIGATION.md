## Mislabeling Risk Matrix Mitigation (v1.0)

Scope: BACKTEST_AND_LIVE_INTEGRITY

### Severity Scale
- HIGH: affects profitability metrics
- MEDIUM: affects decision explainability
- LOW: cosmetic or UI-only

Acceptance Criterion: **no HIGH-severity risk remains unmitigated.**

---

### Risk Coverage

#### 1) TP3_FALSE_POSITIVE (HIGH)
- Description: Trade labeled as TP3 exit even though price never reached TP3.
- Impact: inflated_win_rate, overstated_average_rr
- Mitigations Implemented:
  - exit_price vs tp3_price validation with auto-correction (Step 1)
  - bar_close_confirmed guard prevents intrabar TP3 exits
- Code References:
  - [src/main.py](src/main.py#L1110-L1160) `_execute_exit()` – TP3 reason validation + auto-correct
  - [src/engines/multi_level_tp_engine.py](src/engines/multi_level_tp_engine.py#L140-L210) `evaluate_exit()` – bar-close guard & TP3 validation
- Status: **Mitigated**

#### 2) TP1_PREMATURE_EXIT (HIGH)
- Description: Trade exits immediately after TP1 due to micro pullback.
- Impact: reduced_average_rr, trend_underperformance
- Mitigations Implemented:
  - no_exit_on_same_bar_guard via `bars_since_tp` (Step 2)
  - ATR-based retracement filter (0.25*ATR for TP1) (Step 2)
  - TP1/TP2 decision engines with WAIT/HOLD vs EXIT decisions
- Code References:
  - [src/main.py](src/main.py#L1065-L1086) `_monitor_positions()` – passes tp_transition_time for bars_since_tp
  - [src/engines/strategy_engine.py](src/engines/strategy_engine.py#L572-L655) `evaluate_exit()` – enforces TP1/TP2 decisions
  - [src/engines/tp1_exit_decision_engine.py](src/engines/tp1_exit_decision_engine.py) – micro-pullback HOLD; regime flip EXIT; ATR thresholds
- Status: **Mitigated**

#### 3) SILENT_NO_TRADE (HIGH)
- Description: NO_TRADE decisions without explicit failure reason.
- Impact: impossible_strategy_debugging, false_negative_signal_analysis
- Mitigations Implemented:
  - Structured failure codes for entries (Step 3a)
  - Explicit logging for all NO_EXIT/HOLD decisions on exits (added now)
- Code References:
  - [src/engines/strategy_engine.py](src/engines/strategy_engine.py#L242-L350) `evaluate_entry()` – failure_code tagging
  - [src/engines/strategy_engine.py](src/engines/strategy_engine.py#L630-L720) `evaluate_exit()` – TP1/TP2 HOLD/WAIT logging and NO_EXIT reason with regime context
  - [src/engines/multi_level_tp_engine.py](src/engines/multi_level_tp_engine.py#L140-L230) `evaluate_exit()` – NO_EXIT logging per TP state
- Status: **Mitigated**

#### 4) REGIME_NOT_APPLIED (HIGH)
- Description: Market regime detected but not applied to decision scoring.
- Impact: countertrend_trades, regime_misalignment
- Mitigations Implemented:
  - Regime checks in TP1/TP2 engines; regime flip triggers EXIT
  - Regime context logged for NO_EXIT paths
- Code References:
  - [src/engines/tp1_exit_decision_engine.py](src/engines/tp1_exit_decision_engine.py) – regime flip EXIT
  - [src/engines/tp2_exit_decision_engine.py](src/engines/tp2_exit_decision_engine.py) – regime flip EXIT
  - [src/engines/strategy_engine.py](src/engines/strategy_engine.py#L572-L655) – passes market_regime to TP decision engines; NO_EXIT reason includes regime context
- Status: **Mitigated**

#### 5) BACKTEST_LIVE_DIVERGENCE (HIGH)
- Description: Logic behaves differently in backtest vs live.
- Impact: false_confidence_in_results
- Mitigations Implemented:
  - bar_close_only evaluation enforced (bar_close_confirmed=True) in TP evaluation
  - Shared execution path; no intrabar exits
- Code References:
  - [src/engines/multi_level_tp_engine.py](src/engines/multi_level_tp_engine.py#L140-L210) – bar_close_confirmed guard
  - [src/engines/strategy_engine.py](src/engines/strategy_engine.py#L572-L655) – passes bar_close_confirmed=True
- Status: **Mitigated**

---

### Acceptance Criteria Verification
- Criterion: **no HIGH-severity risk unmitigated** → **PASSED**
- All five HIGH risks have explicit mitigations implemented and logged.
- NO_EXIT/HOLD paths now emit explicit reasons with regime context (SILENT_NO_TRADE closed).
- Regime checks are applied in TP engines (REGIME_NOT_APPLIED closed).
- TP3 price validation and TP3 bar-close guard prevent false positives (TP3_FALSE_POSITIVE closed).
- TP1 guards prevent same-bar exits and filter micro pullbacks (TP1_PREMATURE_EXIT closed).
- Bar-close enforcement ensures backtest/live parity (BACKTEST_LIVE_DIVERGENCE closed).

---

### How to Validate
1) Run acceptance tests (all steps):
   - `pytest tests/test_acceptance_steps_1_2_3.py -v`
2) Check logs for NO_EXIT reasons:
   - Look for `TP1: HOLD`, `TP1: WAIT_NEXT_BAR`, `TP2: HOLD`, `TP2: WAIT_NEXT_BAR`, `NO_EXIT: Position open [REGIME]`
3) Validate regime gating:
   - TP1/TP2 engines: regime flip → EXIT_TRADE
4) Validate TP3 integrity:
   - Exit reasons corrected if price < TP3 (in _execute_exit)
5) Validate bar-close guard:
   - TP exits only triggered on bar close (bar_close_confirmed=True)

---

### Summary
All identified HIGH-severity mislabeling risks are fully mitigated with explicit logging, guards, and validation. The system is ready for backtest and live use without mislabeling-driven false performance interpretations.
