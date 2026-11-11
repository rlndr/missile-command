VERDICT: PASS

## Summary
The diff matches the spec: input actions are renamed, `handle_actions()` owns every transition, the loop opens on the start screen, spawns use game time, and `menu_lines()` drives the centred menus. I ran the suite myself: `73 passed`. Fresh-game tests redirect `CONFIG_PATH` to `tmp_path`, and the worktree is clean.

## Findings
None.
