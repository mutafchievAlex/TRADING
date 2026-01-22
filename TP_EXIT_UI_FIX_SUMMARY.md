# TP1/TP2 Exit Decision UI Integration - Implementation Summary

## Problem
TP Decision панелите в Position таба показваха статични стойности ("Waiting", "HOLD") защото:
- `evaluate_post_tp1_decision` и `evaluate_post_tp2_decision` се извикваха в `evaluate_exit`, но резултатите не се запазваха към позиционното състояние
- UI полета като `post_tp1_decision`, `tp1_exit_reason`, `post_tp2_decision`, `tp2_exit_reason`, `trailing_sl_level` останаха празни
- `StateManager.update_position_tp_state()` актуализираше само `tp_state` и SL, без exit decision метаданните

## Solution
Добавихме персистенция и UI интеграция **БЕЗ** да променяме логиката за вземане на решенията:

### 1. StateManager - Нов метод `update_tp_exit_metadata()` (lines 384-424)
```python
def update_tp_exit_metadata(self, ticket: int,
                            post_tp1_decision: Optional[str] = None,
                            tp1_exit_reason: Optional[str] = None,
                            post_tp2_decision: Optional[str] = None,
                            tp2_exit_reason: Optional[str] = None,
                            trailing_sl_level: Optional[float] = None,
                            trailing_sl_enabled: Optional[bool] = None) -> bool:
```
- Записва TP1/TP2 exit decision метаданни към позицията
- Персистира trailing SL ниво и статус
- Thread-safe с RLock
- Извиква `save_state()` за атомична персистенция

### 2. StateManager - Персистенция в `_build_state_data()` (lines 530-545)
```python
# Ensure TP exit metadata fields are persisted
if 'post_tp1_decision' not in pos_copy:
    pos_copy['post_tp1_decision'] = 'NOT_REACHED'
if 'tp1_exit_reason' not in pos_copy:
    pos_copy['tp1_exit_reason'] = None
# ... TP2 fields, trailing_sl_level, trailing_sl_enabled
```
- Осигурява, че всички TP exit metadata полета са в state.json
- Рестарт зарежда същите полета автоматично

### 3. Main.py - Актуализация на `_monitor_positions()` (lines 1689-1788)
```python
# Capture TP1/TP2 exit decision metadata (NEW)
if tp_state == 'TP1_REACHED' and not should_exit:
    tp1_result = self.strategy_engine.evaluate_post_tp1_decision(...)
    post_tp1_decision = tp1_result.get('decision')
    tp1_exit_reason = tp1_result.get('reason')

if tp_state == 'TP2_REACHED' and not should_exit:
    tp2_result = self.strategy_engine.evaluate_post_tp2_decision(...)
    post_tp2_decision = tp2_result.get('decision')
    tp2_exit_reason = tp2_result.get('reason')
    trailing_sl_level = tp2_result.get('trailing_sl')
    trailing_sl_enabled = trailing_sl_level is not None

# Update state + local position_data for immediate UI
self.state_manager.update_tp_exit_metadata(...)
```
- Извиква TP1/TP2 decision engines когато е в TP1_REACHED/TP2_REACHED състояние
- Запазва метаданните в StateManager
- Актуализира локалния `position_data` за веднага UI рендериране
- **НЕ** променя логиката на `evaluate_exit` - само захваща допълнителните метаданни

## What Changed
✅ **StateManager**
- Нов метод `update_tp_exit_metadata()` за TP1/TP2 метаданни
- Персистенция на 6 нови полета: `post_tp1_decision`, `tp1_exit_reason`, `post_tp2_decision`, `tp2_exit_reason`, `trailing_sl_level`, `trailing_sl_enabled`

✅ **Main.py**
- `_monitor_positions()` извиква TP1/TP2 decision engines при TP1/TP2 състояние
- Записва резултатите в state_manager и локален position_data
- UI получава обогатени position данни с exit decisions

## What Did NOT Change
❌ **Decision Logic** (запазена изцяло)
- `TP1ExitDecisionEngine.evaluate_post_tp1()` - БЕЗ промяна
- `TP2ExitDecisionEngine.evaluate_post_tp2()` - БЕЗ промяна
- `StrategyEngine.evaluate_post_tp1_decision()` - БЕЗ промяна
- `StrategyEngine.evaluate_post_tp2_decision()` - БЕЗ промяна
- `StrategyEngine.evaluate_exit()` - БЕЗ промяна в логиката, само добавихме метаданни захващане в caller

## Expected UI Behavior (После)
### TP1 Decision Panel
- **State**: IN_TRADE / TP1_REACHED / TP2_REACHED
- **Decision**: HOLD / WAIT_NEXT_BAR / EXIT_TRADE (реално от engine)
- **Reason**: "Micro-pullback (0.15 <= 0.25*ATR 0.75); holding for continuation"
- **Bars After TP1**: Инкрементира се при TP1_REACHED
- **Next Exit**: Динамични условия ("Exit on TP1 reach: 2014.00")

### TP2 Decision Panel
- **State**: TP2_REACHED
- **Decision**: HOLD / WAIT_NEXT_BAR / EXIT_TRADE
- **Reason**: "Strong trend continuation after TP2; aiming for TP3"
- **Bars After TP2**: Инкрементира се при TP2_REACHED
- **Trailing SL**: "ACTIVE @ 2017.50" / "2017.50 (INACTIVE)" / "Not set"
- **Next Exit**: "TP2 REACHED @ 2018.00 - Managing to TP3"

## Testing Path
1. Стартирай приложението с demo account
2. Отвори позиция → провери TP1/TP2 панели показват "State: IN_TRADE", "Decision: Waiting"
3. Симулирай достигане на TP1 → провери панелите актуализират на "Decision: HOLD", причина от engine
4. Симулирай ретрейс → провери "Decision: WAIT_NEXT_BAR" или "EXIT_TRADE"
5. Рестартирай приложението → провери state.json съдържа полетата и UI ги зарежда

## Files Modified
- `src/engines/state_manager.py` (2 промени: метод + персистенция)
- `src/main.py` (1 промяна: _monitor_positions метаданни захващане)

## Integration Points
- **Decision Engines** → извикват се от _monitor_positions при правилното състояние
- **State Persistence** → atomic writes в state.json с backups
- **UI Rendering** → main_window.py вече има полета, само чака данните (вече има кода)

## Backward Compatibility
✅ Запазена напълно:
- Позиции без TP state работят като преди (simple SL/TP)
- Стари state.json файлове се зареждат с defaults
- Няма breaking changes в сигнатури или API

## Next Steps (Optional)
- [ ] Добави DEBUG логване за TP1/TP2 decision snapshot на всяка бар-затваряне
- [ ] Добави unit тест за TP1 → HOLD → WAIT → EXIT пътека
- [ ] Добави unit тест за TP2 → HOLD → trailing SL активиране
- [ ] Добави integration тест за state.json персистенция след restart
