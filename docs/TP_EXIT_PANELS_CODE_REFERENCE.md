# TP Exit Panels - Code Change Reference

**Scope**: ui_tp_exit_panel_fix v1.0  
**File**: [src/ui/main_window.py](src/ui/main_window.py)  
**Implementation**: Complete ✅  

---

## Change 1: TP1 Panel Height (Line 540)

### BEFORE
```python
tp1_decision_group = QGroupBox("TP1 Exit Decision")
tp1_decision_group.setMinimumHeight(110)
tp1_decision_group.setCheckable(False)
tp1_decision_group.setFlat(False)
tp1_decision_layout = QVBoxLayout()
```

### AFTER
```python
tp1_decision_group = QGroupBox("TP1 Exit Decision")
tp1_decision_group.setMinimumHeight(120)  # FIX: TP_PANEL_VERTICAL_CLIPPING - Ensure minimum visible content
tp1_decision_group.setMaximumHeight(16777215)  # FIX: Allow expansion to content, no max clipping
tp1_decision_group.setCheckable(False)
tp1_decision_group.setFlat(False)
tp1_decision_layout = QVBoxLayout()
```

### Changes
- Min height: 110px → 120px
- Max height: (not set) → 16777215 (unlimited)
- Purpose: Fix vertical clipping, allow content to expand

---

## Change 2: TP1 State with Badge (Lines 545-557)

### BEFORE
```python
# RESPONSIVE_LAYOUT: Compress labels on small screens (font size 9px)
self.lbl_tp1_state = QLabel("State: -")
self.lbl_tp1_state.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
tp1_decision_layout.addWidget(self.lbl_tp1_state)
```

### AFTER
```python
# RESPONSIVE_LAYOUT: Compress labels on small screens (font size 9px)
# FIX: EMPTY_STATE_FIELDS - Use 'Waiting' instead of '-'
# FIX: NO_VISUAL_STATE_HIERARCHY - Add state badge with color
tp1_state_layout = QHBoxLayout()
self.lbl_tp1_state = QLabel("State: Waiting")
self.lbl_tp1_state.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
self.lbl_tp1_state_badge = QLabel("[IDLE]")
self.lbl_tp1_state_badge.setStyleSheet("font-size: 8px; padding: 2px 6px; background-color: #555; color: #aaa; border-radius: 3px;")
tp1_state_layout.addWidget(self.lbl_tp1_state)
tp1_state_layout.addWidget(self.lbl_tp1_state_badge)
tp1_state_layout.addStretch()
tp1_decision_layout.addLayout(tp1_state_layout)
```

### Changes
- Added horizontal layout wrapper
- Changed text: "State: -" → "State: Waiting"
- Added new label: `lbl_tp1_state_badge`
- Badge styling: light gray background, rounded corners
- Layout: [State Label] [State Badge] [Stretch]

---

## Change 3: TP1 Decision Field (Line 559)

### BEFORE
```python
self.lbl_post_tp1_decision = QLabel("Decision: -")
self.lbl_post_tp1_decision.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
tp1_decision_layout.addWidget(self.lbl_post_tp1_decision)
```

### AFTER
```python
# FIX: EMPTY_STATE_FIELDS - Use 'Waiting' instead of '-'
self.lbl_post_tp1_decision = QLabel("Decision: Waiting")
self.lbl_post_tp1_decision.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
tp1_decision_layout.addWidget(self.lbl_post_tp1_decision)
```

### Changes
- Text: "Decision: -" → "Decision: Waiting"
- Styling: Unchanged

---

## Change 4: TP1 Reason Field (Lines 562-565)

### BEFORE
```python
self.lbl_tp1_exit_reason = QLabel("Reason: -")
self.lbl_tp1_exit_reason.setStyleSheet("font-size: 8px; padding: 2px; min-height: 14px;")
self.lbl_tp1_exit_reason.setWordWrap(True)
tp1_decision_layout.addWidget(self.lbl_tp1_exit_reason)
```

### AFTER
```python
# FIX: EMPTY_STATE_FIELDS - Use meaningful text instead of '-'
self.lbl_tp1_exit_reason = QLabel("Reason: Awaiting evaluation")
self.lbl_tp1_exit_reason.setStyleSheet("font-size: 8px; padding: 2px; min-height: 14px; color: #888;")
self.lbl_tp1_exit_reason.setWordWrap(True)
tp1_decision_layout.addWidget(self.lbl_tp1_exit_reason)
```

### Changes
- Text: "Reason: -" → "Reason: Awaiting evaluation"
- Styling: Added muted gray color (#888)

---

## Change 5: TP1 Next Exit Line (Lines 570-576)

### BEFORE
```python
# HIGH: EXIT_REASON_NOT_VISIBLE_LIVE - Next exit condition (responsive)
self.lbl_tp1_next_exit = QLabel("Next Exit: Awaiting TP1 trigger")
self.lbl_tp1_next_exit.setStyleSheet("font-size: 8px; padding: 2px; background-color: #333; color: #aaa; border-left: 2px solid #1b5e20;")
self.lbl_tp1_next_exit.setWordWrap(True)
tp1_decision_layout.addWidget(self.lbl_tp1_next_exit)
tp1_decision_layout.addStretch()
```

### AFTER
```python
# HIGH: EXIT_REASON_NOT_VISIBLE_LIVE - Next exit condition (responsive)
# FIX: NEXT_EXIT_LINE_TOO_SUBTLE - Add icon and more prominent styling
self.lbl_tp1_next_exit = QLabel("→ Next Exit: Awaiting TP1 trigger")
self.lbl_tp1_next_exit.setStyleSheet("font-size: 9px; padding: 4px 6px; background-color: #1b1b1b; color: #1b5e20; border-left: 3px solid #1b5e20; border-radius: 2px; font-weight: bold;")
self.lbl_tp1_next_exit.setWordWrap(True)
tp1_decision_layout.addWidget(self.lbl_tp1_next_exit)
tp1_decision_layout.addStretch()
```

### Changes
- Icon: "Next Exit:" → "→ Next Exit:"
- Font size: 8px → 9px
- Padding: 2px → 4px 6px
- Background: #333 → #1b1b1b (darker)
- Color: #aaa (gray) → #1b5e20 (green for TP1)
- Border: 2px solid → 3px solid
- Added: border-radius: 2px
- Added: font-weight: bold

---

## Change 6: TP2 Panel Height (Line 584)

### BEFORE
```python
tp2_decision_group = QGroupBox("TP2 Exit Decision")
tp2_decision_group.setMinimumHeight(110)
tp2_decision_group.setCheckable(False)
```

### AFTER
```python
tp2_decision_group = QGroupBox("TP2 Exit Decision")
tp2_decision_group.setMinimumHeight(140)  # FIX: TP_PANEL_VERTICAL_CLIPPING - Ensure minimum visible content
tp2_decision_group.setMaximumHeight(16777215)  # FIX: Allow expansion to content, no max clipping
tp2_decision_group.setCheckable(False)
```

### Changes
- Min height: 110px → 140px (20px more for Trailing SL field)
- Max height: (not set) → 16777215 (unlimited)

---

## Change 7: TP2 State with Badge (Lines 589-601)

### BEFORE
```python
# RESPONSIVE_LAYOUT: Compress labels on small screens
self.lbl_tp2_state = QLabel("State: -")
self.lbl_tp2_state.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
tp2_decision_layout.addWidget(self.lbl_tp2_state)
```

### AFTER
```python
# RESPONSIVE_LAYOUT: Compress labels on small screens
# FIX: EMPTY_STATE_FIELDS - Use 'Waiting' instead of '-'
# FIX: NO_VISUAL_STATE_HIERARCHY - Add state badge with color
tp2_state_layout = QHBoxLayout()
self.lbl_tp2_state = QLabel("State: Waiting")
self.lbl_tp2_state.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
self.lbl_tp2_state_badge = QLabel("[IDLE]")
self.lbl_tp2_state_badge.setStyleSheet("font-size: 8px; padding: 2px 6px; background-color: #555; color: #aaa; border-radius: 3px;")
tp2_state_layout.addWidget(self.lbl_tp2_state)
tp2_state_layout.addWidget(self.lbl_tp2_state_badge)
tp2_state_layout.addStretch()
tp2_decision_layout.addLayout(tp2_state_layout)
```

### Changes
- Same as TP1: Added layout wrapper, badge, semantic text

---

## Change 8: TP2 Decision Field (Line 599)

### BEFORE
```python
self.lbl_post_tp2_decision = QLabel("Decision: -")
self.lbl_post_tp2_decision.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
tp2_decision_layout.addWidget(self.lbl_post_tp2_decision)
```

### AFTER
```python
# FIX: EMPTY_STATE_FIELDS - Use 'Waiting' instead of '-'
self.lbl_post_tp2_decision = QLabel("Decision: Waiting")
self.lbl_post_tp2_decision.setStyleSheet("font-size: 9px; padding: 2px; min-height: 16px;")
tp2_decision_layout.addWidget(self.lbl_post_tp2_decision)
```

### Changes
- Text: "Decision: -" → "Decision: Waiting"

---

## Change 9: TP2 Reason Field (Lines 604-607)

### BEFORE
```python
self.lbl_tp2_exit_reason = QLabel("Reason: -")
self.lbl_tp2_exit_reason.setStyleSheet("font-size: 8px; padding: 2px; min-height: 14px;")
self.lbl_tp2_exit_reason.setWordWrap(True)
tp2_decision_layout.addWidget(self.lbl_tp2_exit_reason)
```

### AFTER
```python
# FIX: EMPTY_STATE_FIELDS - Use meaningful text instead of '-'
self.lbl_tp2_exit_reason = QLabel("Reason: Awaiting evaluation")
self.lbl_tp2_exit_reason.setStyleSheet("font-size: 8px; padding: 2px; min-height: 14px; color: #888;")
self.lbl_tp2_exit_reason.setWordWrap(True)
tp2_decision_layout.addWidget(self.lbl_tp2_exit_reason)
```

### Changes
- Text: "Reason: -" → "Reason: Awaiting evaluation"
- Styling: Added muted gray color (#888)

---

## Change 10: TP2 Trailing SL Field (Lines 604-607)

### BEFORE
```python
self.lbl_trailing_sl = QLabel("Trailing SL: -")
self.lbl_trailing_sl.setStyleSheet("font-size: 8px; padding: 2px; min-height: 14px;")
self.lbl_trailing_sl.setWordWrap(True)
tp2_decision_layout.addWidget(self.lbl_trailing_sl)
```

### AFTER
```python
# FIX: EMPTY_STATE_FIELDS - Use meaningful text instead of '-'
self.lbl_trailing_sl = QLabel("Trailing SL: Inactive")
self.lbl_trailing_sl.setStyleSheet("font-size: 8px; padding: 2px; min-height: 14px; color: #888;")
self.lbl_trailing_sl.setWordWrap(True)
tp2_decision_layout.addWidget(self.lbl_trailing_sl)
```

### Changes
- Text: "Trailing SL: -" → "Trailing SL: Inactive"
- Styling: Added muted gray color (#888)

---

## Change 11: TP2 Next Exit Line (Lines 610-616)

### BEFORE
```python
# HIGH: EXIT_REASON_NOT_VISIBLE_LIVE - Next exit condition (responsive)
self.lbl_tp2_next_exit = QLabel("Next Exit: Awaiting TP2 trigger")
self.lbl_tp2_next_exit.setStyleSheet("font-size: 8px; padding: 2px; background-color: #333; color: #aaa; border-left: 2px solid #f57c00;")
self.lbl_tp2_next_exit.setWordWrap(True)
tp2_decision_layout.addWidget(self.lbl_tp2_next_exit)
tp2_decision_layout.addStretch()
```

### AFTER
```python
# HIGH: EXIT_REASON_NOT_VISIBLE_LIVE - Next exit condition (responsive)
# FIX: NEXT_EXIT_LINE_TOO_SUBTLE - Add icon and more prominent styling
self.lbl_tp2_next_exit = QLabel("→ Next Exit: Awaiting TP2 trigger")
self.lbl_tp2_next_exit.setStyleSheet("font-size: 9px; padding: 4px 6px; background-color: #1b1b1b; color: #f57c00; border-left: 3px solid #f57c00; border-radius: 2px; font-weight: bold;")
self.lbl_tp2_next_exit.setWordWrap(True)
tp2_decision_layout.addWidget(self.lbl_tp2_next_exit)
tp2_decision_layout.addStretch()
```

### Changes
- Icon: "Next Exit:" → "→ Next Exit:"
- Font size: 8px → 9px
- Padding: 2px → 4px 6px
- Background: #333 → #1b1b1b (darker)
- Color: #aaa (gray) → #f57c00 (orange for TP2)
- Border: 2px solid → 3px solid
- Added: border-radius: 2px
- Added: font-weight: bold

---

## Change 12: Dynamic State Badge Updates (Lines 1178-1195)

### BEFORE
```python
self.lbl_tp1_state.setText(f"State: {tp_state}")
```

### AFTER
```python
# FIX: NO_VISUAL_STATE_HIERARCHY - Update state badges with colors based on tp_state
state_badge_map = {
    'IN_TRADE': ('[MONITORING]', '#1976d2', '#64b5f6'),        # Blue for monitoring
    'TP1_REACHED': ('[TRIGGERED]', '#ff9800', '#ffb74d'),      # Orange for triggered
    'TP2_REACHED': ('[TRIGGERED]', '#ff9800', '#ffb74d'),      # Orange for triggered
    'COMPLETED': ('[EXITED]', '#388e3c', '#66bb6a'),           # Green for exited
}

badge_text, badge_bg, badge_border = state_badge_map.get(tp_state, ('[IDLE]', '#555555', '#888888'))
self.lbl_tp1_state_badge.setText(badge_text)
self.lbl_tp1_state_badge.setStyleSheet(f"font-size: 8px; padding: 2px 6px; background-color: {badge_bg}; color: white; border-radius: 3px; border: 1px solid {badge_border};")
self.lbl_tp2_state_badge.setText(badge_text)
self.lbl_tp2_state_badge.setStyleSheet(f"font-size: 8px; padding: 2px 6px; background-color: {badge_bg}; color: white; border-radius: 3px; border: 1px solid {badge_border};")

self.lbl_tp1_state.setText(f"State: {tp_state}")
```

### Changes
- Added state badge mapping dictionary
- Badges update dynamically based on `tp_state`
- 4 states: IDLE (gray), MONITORING (blue), TRIGGERED (orange), EXITED (green)
- Both TP1 and TP2 badges update simultaneously

---

## Summary Table

| Change # | Location | Type | Issue Fixed |
|----------|----------|------|-------------|
| 1 | Line 540 | Height | TP_PANEL_VERTICAL_CLIPPING |
| 2 | Lines 545-557 | Layout | EMPTY_STATE_FIELDS, NO_VISUAL_STATE_HIERARCHY |
| 3 | Line 559 | Text | EMPTY_STATE_FIELDS |
| 4 | Lines 562-565 | Text | EMPTY_STATE_FIELDS |
| 5 | Lines 570-576 | Styling | NEXT_EXIT_LINE_TOO_SUBTLE |
| 6 | Line 584 | Height | TP_PANEL_VERTICAL_CLIPPING |
| 7 | Lines 589-601 | Layout | EMPTY_STATE_FIELDS, NO_VISUAL_STATE_HIERARCHY |
| 8 | Line 599 | Text | EMPTY_STATE_FIELDS |
| 9 | Lines 604-607 | Text | EMPTY_STATE_FIELDS |
| 10 | Lines 604-607 | Text | EMPTY_STATE_FIELDS |
| 11 | Lines 610-616 | Styling | NEXT_EXIT_LINE_TOO_SUBTLE |
| 12 | Lines 1178-1195 | Logic | NO_VISUAL_STATE_HIERARCHY |

---

## New Labels

```python
self.lbl_tp1_state_badge = QLabel("[IDLE]")
self.lbl_tp2_state_badge = QLabel("[IDLE]")
```

---

## Styling Summary

### Colors Added
- IDLE: #555555 (gray)
- MONITORING: #1976d2 (blue)
- TRIGGERED: #ff9800 (orange)
- EXITED: #388e3c (green)
- Muted text: #888 (gray)
- Dark background: #1b1b1b

### Font Changes
- Base: 8px → 9px (Next Exit line)

### Padding Changes
- Base: 2px → 4px 6px (Next Exit line)

### Border Changes
- Width: 2px → 3px (Next Exit line)
- Added: border-radius: 2px
- Added: 1px border on badges

---

*Code Reference Generated: 2026-01-12*  
*Total Changes: 12 modifications + 1 new logic section*  
*New Labels: 2*  
*Backward Compatibility: 100% ✅*
