# BarCloseGuard - Implementation Summary

## Overview
Переработен `BarCloseGuard` че валидира детерминистичност при закрити барове.

## Key Changes

### ✅ MANDATORY Checks (Always Active)
1. **Bar State Validation** (`validate_bar_state`)
   - Проверява DataFrame има >= 2 бара (текущ формиращ се + 1 затворен)
   - Валидира че всички OHLC полета съществуват и не са NaN
   - Проверява логическа консистентност: High >= Open/Close, Low <= Open/Close
   - **Всяко нарушение = ОТКАЗ на сигнала**

2. **Bar Closure Check** (`is_bar_closed`)
   - Проверява че барът е наистина затворен (tiempo >= timeframe)
   - Връща точна причина (минути скоро, остатък време)
   - **Винаги активна, tidak блокира при disable**

### ❌ OPTIONAL Checks (Disabled by Default)

1. **Tick Noise Filter** (`filter_tick_noise`)
   - **Default: DISABLED**
   - Блокира само движения < min_pips_movement (default 0.5)
   - **НЕ блокира добрите setups** ако е disabled
   - При включване: логва warning но НЕ блокира

2. **Anti-FOMO Mode** (`check_anti_fomo_cooldown`)
   - **Default: DISABLED**
   - Логва warning ако < anti_fomo_bars (default 1)
   - **НИКОГА НЕ блокира entry** - само предупреждение
   - Позволява high-quality setups да влязат винаги

### 🔍 Validation Method
```python
validate_entry(df, bar_index=-2, price_movement_pips=None)
```
Ordre на проверки:
1. MANDATORY: Bar state → REJECT если fail
2. OPTIONAL: Anti-FOMO → WARNING (no block)
3. OPTIONAL: Noise filter → REJECT само ако enabled AND fails

### 📝 Rejection Logging
- Всеки отказ логван с точна причина и timestamp
- Категории: `bar-state`, `tick-noise`, `anti-fomo-warning`, `validation-error`
- Методи: `get_rejections_summary()`, `reset_rejections_log()`

### 🎛️ Guard Status
```python
get_guard_status()  # Връща config + rejections
```

## Configuration Examples

### Default (Safest)
```python
guard = BarCloseGuard()
# Всички опционални фильтра са OFF
```

### With Noise Filter
```python
guard = BarCloseGuard(
    min_pips_movement=5.0,
    enable_noise_filter=True  # Now blocks micro-movements
)
```

### Full Protection
```python
guard = BarCloseGuard(
    enable_noise_filter=True,
    enable_anti_fomo=True
    # НО anti-FOMO все още НЕ блокира, само предупреждава
)
```

## Key Principles

✓ **Guard ensures DETERMINISM, NOT strategy changes**
✓ **Mandatory checks always enforced, optional never block good setups**
✓ **All rejections logged with exact reason**
✓ **Optional modes are conservative, additive protection only**
✓ **No high-quality setup is ever rejected by optional filters**

## Integration

```python
from src.engines.bar_close_guard import BarCloseGuard

guard = BarCloseGuard()
approved, reason = guard.validate_entry(df, bar_index=-2)

if approved:
    # Execute trade
    guard.record_signal(current_bar_index)
else:
    logger.error(f"Entry rejected: {reason}")
```

