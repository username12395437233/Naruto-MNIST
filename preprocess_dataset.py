from pathlib import Path
from PIL import Image

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/results")

IMG_SIZE = 224      # timm стандарт
MIN_SIDE = 180      # мелочь пропускаем
JPEG_QUALITY = 92

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
# папки-синонимы (raw_name -> target_class_name)
CLASS_ALIASES = {
    "to_guy": "might_guy",
}


def resize_short_side(img: Image.Image, target: int) -> Image.Image:
    """Resize так, чтобы короткая сторона стала target, сохраняя пропорции."""
    w, h = img.size
    if w <= 0 or h <= 0:
        return img
    if w < h:
        new_w = target
        new_h = int(round(h * (target / w)))
    else:
        new_h = target
        new_w = int(round(w * (target / h)))
    return img.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)


def center_crop(img: Image.Image, size: int) -> Image.Image:
    """Center crop до size x size."""
    w, h = img.size
    left = max(0, (w - size) // 2)
    top = max(0, (h - size) // 2)
    return img.crop((left, top, left + size, top + size))


def process_one(in_path: Path, out_path: Path) -> bool:
    try:
        with Image.open(in_path) as img:
            img = img.convert("RGB")
            w, h = img.size
            if min(w, h) < MIN_SIDE:
                return False

            # 1) сначала подтягиваем короткую сторону до IMG_SIZE
            img = resize_short_side(img, IMG_SIZE)

            # 2) затем центр-кроп до ровно IMG_SIZE x IMG_SIZE
            img = center_crop(img, IMG_SIZE)

            out_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(out_path, format="JPEG", quality=JPEG_QUALITY, optimize=True)

        return True
    except Exception:
        return False


def main():
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"RAW_DIR not found: {RAW_DIR.resolve()}")

    source_dir = RAW_DIR / "to_guy"
    if not source_dir.exists():
        raise FileNotFoundError(f"Source folder not found: {source_dir.resolve()}")

    target_class = "might_guy"
    out_class_dir = OUT_DIR / target_class
    out_class_dir.mkdir(parents=True, exist_ok=True)

    files = [p for p in source_dir.rglob("*")
             if p.is_file() and p.suffix.lower() in IMG_EXTS]

    print(f"[to_guy -> {target_class}] found {len(files)} files")

    existing = list(out_class_dir.glob("*.jpg"))
    idx = len(existing) + 1

    total = ok = bad = 0

    for f in files:
        total += 1
        out_path = out_class_dir / f"{target_class}_{idx:04d}.jpg"
        if process_one(f, out_path):
            ok += 1
            idx += 1
        else:
            bad += 1

    print(f"[{target_class}] total images now: {idx - 1}")
    print("\nDone.")
    print(f"Total files processed: {total}")
    print(f"Processed OK        : {ok}")
    print(f"Skipped / Bad       : {bad}")
    print(f"Output dir          : {out_class_dir.resolve()}")



if __name__ == "__main__":
    main()
