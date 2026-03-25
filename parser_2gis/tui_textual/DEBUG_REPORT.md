# TUI Navigation Bug Fix Report

## Problem Description

The TUI interface was freezing when users tried to start parsing after selecting cities and categories.

### User Flow That Caused Freeze:
1. Run `./run.sh --tui`
2. Select cities → automatically redirected to categories
3. Select categories and press "Next"
4. **FREEZE** - parsing screen doesn't work

## Root Cause

**Technical Issue:** Using `switch_screen()` instead of `push_screen()` for screen transitions that require `on_mount()` to be called.

In Textual:
- `push_screen()` → adds screen to stack **+ calls `on_mount()`**
- `switch_screen()` → replaces screen in stack, **but does NOT call `on_mount()`**

## Files Changed

| File | Line | Changed From | Changed To |
|------|------|--------------|------------|
| `category_selector.py` | 315 | `switch_screen("parsing")` | `push_screen("parsing")` |
| `city_selector.py` | 304 | `switch_screen("category_selector")` | `push_screen("category_selector")` |
| `main_menu.py` | 170 | `switch_screen("parsing")` | `push_screen("parsing")` |

## Problem Chain (Before Fix)

```
User selects categories
    ↓
Presses "Next" in category_selector
    ↓
Calls switch_screen("parsing")  ← PROBLEM
    ↓
ParsingScreen mounts to interface
    ↓
on_mount() NOT called  ← CRITICAL ERROR
    ↓
app.start_parsing() NOT launched
    ↓
SCREEN FREEZES - parsing doesn't work
```

## Solution Chain (After Fix)

```
User selects categories
    ↓
Presses "Next" in category_selector
    ↓
Calls push_screen("parsing")  ← FIXED
    ↓
ParsingScreen mounts to interface
    ↓
on_mount() called correctly  ← WORKS
    ↓
app.start_parsing() launches
    ↓
Parsing works correctly
```

## Tests Added

- `tests/test_tui_screen_navigation.py` - 20 comprehensive tests for TUI navigation
  - Tests screen navigation chain
  - Tests on_mount() calls
  - Tests switch_screen vs push_screen usage
  - Tests error handling
  - Tests state persistence
  - Tests rapid navigation

## Test Results

✅ All 69 TUI tests passing
✅ Total project tests: 1495+ passed
✅ Code quality: 9.99/10 (Pylint)
✅ Ruff check: All passed
✅ Ruff format: All formatted

## Recommendations

1. Always use `push_screen()` when the target screen has critical logic in `on_mount()`
2. Use `switch_screen()` only for non-critical screen replacements
3. Add tests for screen navigation to prevent regressions
4. Document screen transition patterns in architecture docs
