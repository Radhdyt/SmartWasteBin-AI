import os
import shutil
import random
from pathlib import Path
from tqdm import tqdm

# Constants
SRC_ROOT = Path("DATASET")
DST_ROOT = Path("data/waste_cls")
SEED = 42

# Mapping: 'O' -> 'organic', 'R' -> 'non_organic'
CLASS_MAPPING = {
    "O": "organic",
    "R": "non_organic"
}

def setup_dirs():
    """Create destination directory structure."""
    if DST_ROOT.exists():
        print(f"Warning: {DST_ROOT} already exists. Merging/Overwriting...")
    
    for split in ["train", "val", "test"]:
        for label_name in CLASS_MAPPING.values():
            (DST_ROOT / split / label_name).mkdir(parents=True, exist_ok=True)

def get_image_files(path):
    """Recursively get image files from a directory."""
    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    return [p for p in path.rglob("*") if p.suffix.lower() in valid_exts]

def copy_files(files, split_name, dst_root=DST_ROOT):
    """Copy files to destination based on split and class mapping."""
    print(f"Propagating {len(files)} files to {split_name}...")
    for src_path in tqdm(files):
        # Determine class from parent folder name (O or R)
        # Assuming structure: DATASET/TRAIN/O/image.jpg
        parent_name = src_path.parent.name
        
        if parent_name not in CLASS_MAPPING:
            print(f"Skipping {src_path} (unknown class folder: {parent_name})")
            continue
            
        target_class = CLASS_MAPPING[parent_name]
        dst_path = dst_root / split_name / target_class / src_path.name
        
        # Avoid unnecessary copy if exists and size matches
        if not dst_path.exists():
             shutil.copy2(src_path, dst_path)

def main():
    random.seed(SEED)
    setup_dirs()
    
    # 1. Process TRAIN -> train (80%) + val (20%)
    print("Processing TRAIN dataset for Train/Val split...")
    train_src = SRC_ROOT / "TRAIN"
    
    total_train_count = 0
    total_val_count = 0
    
    for class_code in CLASS_MAPPING.keys():
        src_dir = train_src / class_code
        if not src_dir.exists():
            print(f"Warning: {src_dir} does not exist!")
            continue
            
        images = get_image_files(src_dir)
        random.shuffle(images)
        
        split_idx = int(len(images) * 0.8)
        train_files = images[:split_idx]
        val_files = images[split_idx:]
        
        copy_files(train_files, "train")
        copy_files(val_files, "val")
        
        total_train_count += len(train_files)
        total_val_count += len(val_files)

    # 2. Process TEST -> test (100%)
    print("\nProcessing TEST dataset...")
    test_src = SRC_ROOT / "TEST"
    total_test_count = 0
    
    for class_code in CLASS_MAPPING.keys():
        src_dir = test_src / class_code
        if not src_dir.exists():
             print(f"Warning: {src_dir} does not exist!")
             continue
             
        images = get_image_files(src_dir)
        copy_files(images, "test")
        total_test_count += len(images)

    print("\n=== Data Preparation Complete ===")
    print(f"Output Directory: {DST_ROOT.absolute()}")
    print(f"Train images: {total_train_count}")
    print(f"Val images:   {total_val_count}")
    print(f"Test images:  {total_test_count}")
    
    # Validation of counts per class
    print("\nDetailed Counts:")
    for split in ["train", "val", "test"]:
        print(f"[{split.upper()}]")
        for cls_name in CLASS_MAPPING.values():
            count = len(list((DST_ROOT / split / cls_name).glob("*")))
            print(f"  {cls_name}: {count}")

if __name__ == "__main__":
    main()
