from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
IMPORTANT_DIR = REPO_ROOT / "important"
FRONTEND_DIR = IMPORTANT_DIR / "frontend"


def test_demo_video_asset_exists():
    """Verify demo.mp4 is correctly placed in frontend public directory and is valid."""
    public_video = FRONTEND_DIR / "public" / "demo.mp4"
    assert public_video.exists(), f"Expected video at {public_video}"
    assert public_video.stat().st_size > 1_000_000, "demo.mp4 should be non-empty and > 1MB"


def test_guide_config_integrity():
    """Verify guideConfig.ts specifies the official GitHub repository and video path."""
    config_file = FRONTEND_DIR / "src" / "config" / "guideConfig.ts"
    assert config_file.exists(), "guideConfig.ts must exist"
    content = config_file.read_text(encoding="utf-8")
    assert "https://github.com/putbullet/compust" in content
    assert "'/demo.mp4'" in content or '"/demo.mp4"' in content


def test_root_readme_has_required_sections():
    """Verify the root README.md contains honest expectations, limitations, and contributor guidelines."""
    readme_file = REPO_ROOT / "README.md"
    assert readme_file.exists(), "Root README.md must exist"
    content = readme_file.read_text(encoding="utf-8")

    assert "Please Read Before Using Compust" in content
    assert "What Compust IS" in content
    assert "What Compust IS NOT" in content
    assert "LinkedIn" in content
    assert "Cloudflare" in content
    assert "Scraper & Parser Contributor Guide" in content
    assert "https://github.com/putbullet/compust" in content


def test_guide_frontend_components_exist():
    """Verify GuideView and FloatingHelpControls exist."""
    guide_view = FRONTEND_DIR / "src" / "components" / "Guide" / "GuideView.tsx"
    guide_css = FRONTEND_DIR / "src" / "components" / "Guide" / "GuideView.css"
    floating_controls = FRONTEND_DIR / "src" / "components" / "Guide" / "FloatingHelpControls.tsx"

    assert guide_view.exists(), "GuideView.tsx must exist"
    assert guide_css.exists(), "GuideView.css must exist"
    assert floating_controls.exists(), "FloatingHelpControls.tsx must exist"

    # Verify GuideView contains key required sections
    content = guide_view.read_text(encoding="utf-8")
    assert "Welcome to Compust" in content
    assert "Please read this before using Compust" in content
    assert "See Compust in Action" in content
    assert "How Compust Works" in content
    assert "Scraper Architecture" in content
    assert "Getting Started: A-to-Z Workflow" in content
    assert "Developer & Contributor Guide" in content
    assert "Frequently Asked Questions" in content
    assert "video" in content.lower()
