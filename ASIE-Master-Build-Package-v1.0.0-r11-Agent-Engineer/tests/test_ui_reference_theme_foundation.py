from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "src" / "asie-reference-theme.css"
MAIN = ROOT / "src" / "main.tsx"


APPROVED_TOKENS = {
    "--asie-bg": "#f5f7f3",
    "--asie-bg-secondary": "#edf2eb",
    "--asie-card": "#ffffff",
    "--asie-card-secondary": "#f4f7f2",
    "--asie-border": "#dfe6db",
    "--asie-border-soft": "#e7ece2",
    "--asie-brand": "#12805c",
    "--asie-brand-dark": "#0b6246",
    "--asie-amber": "#d97706",
    "--asie-teal": "#0d9488",
    "--asie-danger": "#dc2626",
    "--asie-text-primary": "#102b21",
    "--asie-text-secondary": "#46574e",
    "--asie-text-muted": "#7d8c83",
}


def test_reference_theme_is_loaded_after_legacy_styles() -> None:
    source = MAIN.read_text(encoding="utf-8")
    legacy_import = 'import "./styles.css";'
    theme_import = 'import "./asie-reference-theme.css";'
    assert legacy_import in source
    assert theme_import in source
    assert source.index(legacy_import) < source.index(theme_import)


def test_approved_reference_palette_is_exact() -> None:
    source = THEME.read_text(encoding="utf-8").lower()
    for token, value in APPROVED_TOKENS.items():
        assert f"{token}: {value};" in source, token


def test_theme_covers_landing_and_authenticated_shell() -> None:
    source = THEME.read_text(encoding="utf-8")
    required_selectors = (
        ".landing-page",
        ".landing-nav",
        ".landing-hero--immersive",
        ".decision-orbit",
        ".service-ribbon",
        ".decision-flow",
        ".app-shell",
        ".app-shell > .sidebar",
        ".workspace > .topbar",
        ".nav-item--active",
    )
    for selector in required_selectors:
        assert selector in source, selector


def test_theme_declares_visual_only_boundary() -> None:
    source = THEME.read_text(encoding="utf-8")
    assert "visual presentation only" in source
    assert "No runtime, contract, finance, snapshot" in source
