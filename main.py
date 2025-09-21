import os
import shutil
import hashlib
import exifread
from datetime import datetime
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()


def get_file_hash(path):
    """Compute SHA256 hash of file for binary comparison."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_shooting_date(path):
    """Extract shooting date from EXIF, fallback to file modified date."""
    ext = os.path.splitext(path)[1].lower()

    # Handle HEIC/HEIF files
    if ext in ['.heic', '.heif']:
        try:
            with Image.open(path) as img:
                exif_data = img.getexif()
                date_str = exif_data.get(36867) or exif_data.get(306)  # DateTimeOriginal or DateTime
                if date_str:
                    return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S").strftime("%Y%m%d")
        except Exception:
            pass
    
    # For other image types
    with open(path, "rb") as f:
        tags = exifread.process_file(f, details=False)

    date_tag = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
    if date_tag:
        try:
            with pyexiv2.Image(path) as img:
                exif_dict = img.read_exif()
                # Try different EXIF date tags
                for tag in ['Exif.Photo.DateTimeOriginal', 'Exif.Image.DateTime', 'Exif.Photo.DateTimeDigitized']:
                    if tag in exif_dict:
                        date_str = exif_dict[tag]
                        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S").strftime("%Y%m%d")
        except Exception as e:
            print(f"Warning: Could not read EXIF from {path}: {e}")
    
    # For traditional formats (JPEG, TIFF) or fallback for HEIC/HEIF
    if file_ext not in ('.heic', '.heif'):
        try:
            with open(path, "rb") as f:
                tags = exifread.process_file(f, details=False)

            date_tag = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
            if date_tag:
                try:
                    return datetime.strptime(str(date_tag), "%Y:%m:%d %H:%M:%S").strftime("%Y%m%d")
                except Exception:
                    pass
        except Exception as e:
            print(f"Warning: Could not read EXIF from {path}: {e}")

    # Fallback: use filesystem modified time
    mtime = os.path.getmtime(path)
    return datetime.fromtimestamp(mtime).strftime("%Y%m%d")

def copy_images(src_dirs, dest_dir, log_path="conflict_log.txt", seen_source_log_path="seen_sources.txt", available_types=('.jpg', '.jpeg', '.png', '.cr2', '.heic', '.heif')):
    
    if not os.path.exists(dest_dir):
        print(f"Destination directory {dest_dir} does not exist. Aborting.")
        return
    
    seen = {}   # filename → (hash, final_path)
    seen_src = [] # store seen source
    hashes = {} # hash → list of filenames
    log = []

    # check for source dirs
    for src in src_dirs:
        if not os.path.exists(src):
            print(f"Source directory {src} does not exist. Aborting.")
            return
        
    # check for destination dir
    if not os.path.exists(dest_dir):
        print(f"Destination directory {dest_dir} does not exist. Aborting.")
        return
    
    if not os.listdir(dest_dir):
        print(f"Destination directory {dest_dir} is empty. Proceeding with copy.")

    # check for seen sources log
    if os.path.exists(seen_source_log_path):
        with open(seen_source_log_path, "r") as f:
            for line in f:
                seen_src.append(line.strip())

    ####### Verbose params #######
    print("=" * 10, "Status", "=" * 10)
    for i, src in enumerate(src_dirs, 1):
        print(f"Source {i}: {src}")
    print(f"Destination: {dest_dir}", end=' ')
    if os.listdir(dest_dir):
        print("**not empty**")
    else:
        print("(empty)")

    if os.path.exists(seen_source_log_path):
        print(f"Previous seen sources found. To re-backup all sources, delete the {seen_source_log_path} file.")
    print("=" * 28)

    if input("Proceed? (y/n): ").lower() != 'y':
        print("Aborting.")
        return


    total_files = sum(len(files) for src in src_dirs for _, _, files in os.walk(src))
    processed = 0

    for src in src_dirs:
        for root, _, files in os.walk(src):
            for name in files:
                processed += 1
                
                if not name.lower().endswith(available_types):
                    continue


                print('({}/{})'.format(processed, total_files), end=' ')

                src_path = os.path.join(root, name)
                file_hash = get_file_hash(src_path)

                if src_path in seen_src:
                    print(f"Already processed source, skipping: {src_path}")
                    continue

                seen_src.append(src_path)

                if name in seen:
                    prev_hash, prev_path = seen[name]

                    if file_hash == prev_hash:
                        # Same filename, same photo → skip copy
                        print(f"Skip duplicate: {src_path}")
                        continue
                    else:
                        # Same filename, different photo
                        shooting_date = get_shooting_date(src_path)
                        new_name = f"{shooting_date}_{name}"
                        base, ext = os.path.splitext(new_name)

                        # rename prev_path
                        prev_shooting_date = get_shooting_date(prev_path)
                        prev_new_name = f"{prev_shooting_date}_{os.path.basename(prev_path)}"
                        os.rename(prev_path, os.path.join(dest_dir, prev_new_name))

                        # Resolve further conflicts (_0, _1...)
                        counter = 0
                        while os.path.exists(os.path.join(dest_dir, new_name)):
                            new_name = f"{base}_{counter}{ext}"
                            counter += 1

                        dest_path = os.path.join(dest_dir, new_name)
                        shutil.copy2(src_path, dest_path)
                        seen[new_name] = (file_hash, dest_path)
                        hashes.setdefault(file_hash, []).append(new_name)
                        print(f"Renamed and copied: {src_path} → {dest_path}")

                else:
                    # Check if different filename but same photo
                    if file_hash in hashes:
                        log.append(f"Different filename, same photo: {src_path} matches {hashes[file_hash]}")
                        # Still copy both (different names)
                        # dest_path = os.path.join(dest_dir, name)
                        # shutil.copy2(src_path, dest_path)
                        seen[name] = (file_hash, dest_path)
                        hashes[file_hash].append(name)

                        # print(f"Copied with different name: {src_path} → {dest_path}")
                        print(f"Same photo with {dest_path}, skipping copy: {src_path}")
                    else:
                        # Normal copy
                        dest_path = os.path.join(dest_dir, name)
                        shutil.copy2(src_path, dest_path)
                        seen[name] = (file_hash, dest_path)
                        hashes[file_hash] = [name]

                        print(f"Copied: {src_path} → {dest_path}")
                

    # Write conflict log
    if log:
        with open(log_path, "w") as f:
            f.write("\n".join(log))
        print(f"Conflicts logged to {log_path}")

    # Write seen source log
    with open(seen_source_log_path, "w") as f:
        f.write("\n".join(seen_src))
    print(f"Seen sources logged to {seen_source_log_path}")

    print("\nDone.")

if __name__ == "__main__":
    src_dirs = ["./src1", "./src2"]
    dest_dir = "./dest"
    available_types = ('.jpg', '.jpeg', '.png', '.cr2', '.heic', '.heif')
    copy_images(src_dirs, dest_dir, available_types=available_types)
