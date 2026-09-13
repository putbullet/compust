"""Generate multi-resolution Windows .ico icon from Compust logo-transparent.png."""

from pathlib import Path
from PIL import Image


def generate_ico(png_path: Path, output_ico_path: Path) -> Path:
    """Generate multi-resolution .ico from a source PNG."""
    if not png_path.exists():
        raise FileNotFoundError(f"Source PNG not found at: {png_path}")

    output_ico_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(png_path)
    
    # Ensure RGBA mode for transparency preservation
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(
        output_ico_path,
        format="ICO",
        sizes=sizes,
    )
    return output_ico_path


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    source_png = repo_root / "important" / "frontend" / "public" / "logo-transparent.png"
    target_ico = repo_root / "launcher" / "compust.ico"

    print(f"Generating icon from {source_png} -> {target_ico}")
    out = generate_ico(source_png, target_ico)
    print(f"Successfully generated {out} ({out.stat().st_size} bytes)")
