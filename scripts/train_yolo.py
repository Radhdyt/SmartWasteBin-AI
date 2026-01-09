from ultralytics import YOLO
import os
import torch

def train():
    # 0. Check GPU
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\n[INFO] Training running on: {device.upper()}")
    if device == 'cuda':
        print(f"[INFO] GPU: {torch.cuda.get_device_name(0)}")
        print("-" * 30)

    # 1. Load Pre-trained Model (Transfer Learning)
    print("[INFO] Loading YOLOv8n model...")
    model = YOLO('yolov8n.pt')  # using nano model for speed

    # 2. Define Dataset Path
    # Absolute path to the data.yaml file we just edited
    yaml_path = r"C:\Users\Rad\Downloads\Github\IOT-main\DATASET_YOLO\data.yaml"

    # 3. Train
    print(f"[INFO] Starting training with {yaml_path}...")
    # epochs=50 is decent for a start. imgsz=640 is standard.
    results = model.train(
        data=yaml_path,
        epochs=50,
        imgsz=640,
        batch=16,
        name='sampah_indo_run',
        patience=10  # Stop early if no improvement
    )

    # 4. Success Message
    print("[SUCCESS] Training Completed!")
    try:
        # Try to get save_dir from trainer if available
        save_dir = model.trainer.save_dir
        print(f"[INFO] Best model saved at: {save_dir}/weights/best.pt")
    except:
        # Fallback
        print(f"[INFO] Check the 'runs/detect' folder for 'sampah_indo_runX/weights/best.pt'")

if __name__ == '__main__':
    train()
