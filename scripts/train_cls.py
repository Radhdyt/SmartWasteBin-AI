from ultralytics import YOLO
import os

# Constants
DATA_DIR = os.path.abspath("data/waste_cls")
MODEL_NAME = "yolov8n-cls.pt"
EPOCHS = 30
IMGSZ = 224
BATCH_SIZE = 64
PROJECT = "runs/classify"
NAME = "train"

def main():
    # 1. Initialize Model
    print(f"Loading model {MODEL_NAME}...")
    model = YOLO(MODEL_NAME)

    # 2. Train
    print(f"Starting training on {DATA_DIR}...")
    # YOLO classification requires the data arg to point to the directory containing train/val/test folders
    results = model.train(
        data=DATA_DIR,
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH_SIZE,
        project=PROJECT,
        name=NAME,
        exist_ok=True, # Overwrite existing project/name experiment
        cache=True     # Cache images for faster training
    )

    # 3. Validate
    print("Validating model...")
    metrics = model.val()
    print(f"Top-1 Accuracy: {metrics.top1:.4f}")

    # 4. Export (optional, usually best.pt is saved automatically)
    print(f"Training complete. Best model saved at: {os.path.join(PROJECT, NAME, 'weights', 'best.pt')}")

if __name__ == "__main__":
    main()
