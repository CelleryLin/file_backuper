# Image Merge with SHA256 + EXIF Metadata

This Python project merges images from multiple source folders into a single destination folder while handling duplicates and conflicts based on **binary file identity (SHA256)** and **EXIF shooting date**.

---

## Features

1. **Merge multiple folders** safely into a destination.
2. **Duplicate handling**:

   * Same filename + same photo → skip one.
   * Same filename + different photo → rename using `<shooting_date>_<original_filename>` (suffix `_0, _1…` if needed).
   * Different filename + same photo → skip copying but log conflict.
3. **Track processed files** via `seen_sources.txt` to avoid reprocessing.
4. **Flexible file types** via `available_types`.
5. Verbose progress with counters, prompts, and status messages.

---

## Requirements

```txt
numpy>=1.26.0
pillow>=10.0.0
imagehash>=4.3
exifread>=3.0.0
```

Install dependencies with:

```bash
pip install -r requirements.txt
```

---

## Usage
See `main.py` for an example.

```python
if __name__ == "__main__":
    src_dirs = ["./src1", "./src2"]
    dest_dir = "./dest"
    available_types = ('.jpg', '.jpeg', '.png', '.cr2')
    copy_images(
        src_dirs, 
        dest_dir, 
        available_types=available_types
    )
```

**Parameters:**

* `src_dirs`: list of source directories.
* `dest_dir`: destination folder. Must exist.
* `available_types`: tuple of allowed file extensions.
* `log_path`: path to conflict log file (`conflict_log.txt`).
* `seen_source_log_path`: path to track processed files (`seen_sources.txt`).

---

## How It Works

1. Computes **SHA256 hash** for each file to detect duplicates.
2. Extracts EXIF `DateTimeOriginal` (or fallback to modified date) for renaming.
3. Resolves conflicts by renaming or skipping according to rules.
4. Copies files safely to the destination folder.
5. Logs conflicts and processed sources.

---

## Notes

* Works for JPEG, PNG, RAW (e.g., CR2) images.
* Avoid re-processing previously backed-up sources by keeping `seen_sources.txt`.