from pathlib import Path
from icrawler.builtin import BingImageCrawler
from icrawler.downloader import ImageDownloader
from PIL import Image
import re


# ====== НАСТРОЙКИ ======
OUT_DIR = Path("data/raw3")
PER_CLASS = 200
START_INDEX = 400

MIN_SIDE = 220  # чуть выше, чтобы было меньше миниатюр/иконок

# Фразы, которые хотим видеть (помогает отсечь левое)
ALLOW_HINTS = [
    "naruto", "shippuden", "anime", "episode", "frame", "screenshot"
]

# Мусорные слова: косплей, фигурки, товары, обои, арты, манга и т.п.
BLOCK_WORDS = [
    "cosplay", "真人", "live action", "actor", "actress",
    "figure", "figurine", "toy", "funko", "nendoroid", "model", "statue",
    "poster", "wallpaper", "hd wallpaper", "4k", "8k", "background",
    "merch", "t-shirt", "shirt", "hoodie", "mug", "sticker", "keychain",
    "drawing", "fanart", "fan art", "artwork", "deviantart", "pixiv",
    "manga", "panel", "scan", "cover", "coloring",
    "amv", "edit", "collage", "meme", "gif",
    "roblox", "minecraft", "gacha",
]

BLOCK_RE = re.compile("|".join(re.escape(w) for w in BLOCK_WORDS), re.IGNORECASE)
ALLOW_RE = re.compile("|".join(re.escape(w) for w in ALLOW_HINTS), re.IGNORECASE)


# Более “серийные” запросы: именно кадры/фреймы/скриншоты
CLASSES = {
    "kakashi": [
        "Kakashi Hatake Naruto episode screenshot",
        "Kakashi Hatake Naruto Shippuden episode screenshot",
        "Kakashi Hatake anime frame screenshot",
        "Kakashi Hatake Naruto screenshot face close up",
        "Kakashi Hatake without mask anime episode screenshot",
    ],
    "naruto": [
        "Naruto Uzumaki Naruto episode screenshot",
        "Naruto Uzumaki Naruto Shippuden episode screenshot",
        "Naruto Uzumaki anime frame screenshot",
        "Naruto Uzumaki screenshot face close up",
        "Naruto Uzumaki sage mode episode screenshot",
    ],
    "sasuke": [
        "Sasuke Uchiha Naruto episode screenshot",
        "Sasuke Uchiha Naruto Shippuden episode screenshot",
        "Sasuke Uchiha anime frame screenshot",
        "Sasuke Uchiha screenshot face close up",
        "Sasuke Uchiha sharingan episode screenshot",
    ],
    "might_guy": [
        "Might Guy Naruto episode screenshot",
        "Might Guy Naruto Shippuden episode screenshot",
        "Might Guy anime frame screenshot",
        "Might Guy screenshot face close up",
        "Maito Gai eighth gate episode screenshot",
    ],
}


# ====== УТИЛИТЫ ======
def rename_files(folder: Path, class_name: str, start_index: int):
    files = sorted([p for p in folder.iterdir() if p.is_file()], key=lambda x: x.name)
    for i, p in enumerate(files):
        new_name = f"{class_name}_{start_index + i:04d}.jpg"
        new_path = folder / new_name
        if p.name == new_name:
            continue
        if new_path.exists():
            continue
        p.rename(new_path)


def ensure_rgb_and_min_size(img_path: Path, min_side: int = MIN_SIDE) -> bool:
    try:
        with Image.open(img_path) as im:
            im.load()
            w, h = im.size
            if min(w, h) < min_side:
                img_path.unlink(missing_ok=True)
                return False

            if im.mode != "RGB":
                im = im.convert("RGB")
                im.save(img_path, quality=92, optimize=True)

        return True
    except Exception:
        img_path.unlink(missing_ok=True)
        return False


def looks_like_trash(text: str) -> bool:
    """
    True -> это мусор (косплей/фигурки/обои/арты/манга/мемы...)
    """
    if not text:
        return False
    return bool(BLOCK_RE.search(text))


def looks_like_anime_frame(text: str) -> bool:
    """
    True -> есть признаки что это кадр/скриншот из аниме
    """
    if not text:
        return False
    return bool(ALLOW_RE.search(text))


class CleanAnimeDownloader(ImageDownloader):
    def download(self, task, default_ext, timeout=5, max_retry=3, overwrite=False, **kwargs):
        meta = task.get("meta", {}) or {}

        url = str(meta.get("url", "") or meta.get("image", "") or "")
        src = str(meta.get("source_url", "") or meta.get("referer", "") or "")  
        title = str(meta.get("title", "") or meta.get("desc", "") or "")

        combined = " ".join([url, src, title]).strip()

        # Если мета пустая — НЕ блокируем (иначе будут пустые папки)
        if combined:
            # 1) блокируем явный мусор
            if looks_like_trash(combined):
                return None

            # 2) НЕ требуем "anime/screenshot/episode" (это слишком жёстко)
            #    (если хочешь обратно — включишь позже)

        return super().download(task, default_ext, timeout=timeout, max_retry=max_retry, overwrite=overwrite, **kwargs)



# ====== ОСНОВНОЙ КОД ======
def postprocess_folder(folder: Path):
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    for p in list(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in exts:
            ensure_rgb_and_min_size(p)


def download_for_class(class_name: str, queries: list[str], target: int):
    class_dir = OUT_DIR / class_name
    class_dir.mkdir(parents=True, exist_ok=True)

    existing = [p for p in class_dir.iterdir() if p.is_file()]
    if len(existing) >= target:
        print(f"[{class_name}] already has {len(existing)} files, skipping.")
        return

    need = target - len(existing)
    print(f"[{class_name}] downloading ~{need} images into {class_dir}")

    crawler = BingImageCrawler(
        storage={"root_dir": str(class_dir)},
        downloader_cls=CleanAnimeDownloader,   # <-- ВОТ ТУТ ФИЛЬТР
        feeder_threads=1,
        parser_threads=1,
        downloader_threads=4,
    )

    # запас, потому что фильтр/чистка удалит часть
    to_download = int(need * 3.0)

    for q in queries:
        if len([p for p in class_dir.iterdir() if p.is_file()]) >= target:
            break

        print(f"  query: {q}")
        crawler.crawl(
            keyword=q,
            max_num=to_download,
            filters={
                "size": "large",
            },
        )

        postprocess_folder(class_dir)

    # финальная подгонка
    files = sorted([p for p in class_dir.iterdir() if p.is_file()], key=lambda x: x.name)
    if len(files) > target:
        for p in files[target:]:
            p.unlink(missing_ok=True)

    # переименование с START_INDEX
    rename_files(class_dir, class_name, START_INDEX)

    print(f"[{class_name}] total now: {len([p for p in class_dir.iterdir() if p.is_file()])}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output dir: {OUT_DIR.resolve()}")
    print(f"Per class target: {PER_CLASS}")

    for cls, queries in CLASSES.items():
        download_for_class(cls, queries, PER_CLASS)


if __name__ == "__main__":
    main()
