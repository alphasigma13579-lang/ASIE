# Project-local Graphify runtime and provenance

Official source: https://github.com/Graphify-Labs/graphify

Reviewed source commit: `86c57be8204673c2a1b9849a3292a7dd3ab373d8` (branch `v8`). Its `pyproject.toml` declares `graphifyy` version `0.9.92`, Python >=3.10 and the `graphify` CLI. Package metadata was independently checked after installation. Upstream licenses are Apache-2.0 and retained MIT portions; this adapter does not vendor upstream implementation or skill text.

Official upstream Codex skill and installer reviewed:

- https://github.com/Graphify-Labs/graphify/blob/86c57be8204673c2a1b9849a3292a7dd3ab373d8/graphify/skill-codex.md
- https://github.com/Graphify-Labs/graphify/blob/86c57be8204673c2a1b9849a3292a7dd3ab373d8/graphify/install.py
- Codex discovery specification: https://learn.chatgpt.com/docs/build-skills

The upstream Codex installer targets `.codex/skills/graphify`, writes an always-on section into `AGENTS.md`, and registers `.codex/hooks.json`. Its full workflow also permits global auto-install/upgrade, GitHub cloning and semantic extraction. This installation instead places a small ASIE adapter in the documented repository scope `.agents/skills/graphify/` and uses the official CLI directly. Neither upstream installer nor its automatic setup blocks should be run for ASIE under this grant.

## Setup when a filesystem project is authorized

Run from the authorized repository root with Python >=3.10. Confirm that the `.venv` destination is inside this skill, is not a symlink/junction, and does not already hold another environment. Installation downloads public packages; it sends no ASIE source to PyPI. Do not silently replace an existing environment or install optional extras.

```powershell
python -m venv .agents/skills/graphify/.venv
if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
$graphifyPython = Join-Path (Get-Location) '.agents/skills/graphify/.venv/Scripts/python.exe'
& $graphifyPython -m pip install --index-url https://pypi.org/simple --only-binary=:all: -r .agents/skills/graphify/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Graphify installation failed' }
& $graphifyPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Graphify dependency check failed' }
& $graphifyPython -c "from importlib.metadata import version; print(version('graphifyy'))"
```

The direct dependency is pinned; transitive dependencies are resolved by pip and are not fully locked. Capture their actual versions in validation evidence. If compatible binary wheels are unavailable, stop and report the platform requirement instead of compiling or changing Python globally.

After the skill reaches the working branch used by Codex, it should be available on the next turn as `$graphify`. Verify it in the skill selector; restart Codex if discovery has not refreshed. A remote PR alone does not load a skill into this chat.

## Rollback

Revert the commit adding this skill through normal repository review. Runtime and graph outputs are disposable, untracked local artifacts; remove only verified project-owned paths if cleanup is separately requested. No application rollback, global uninstall, Claude edits or AAS changes are needed.
