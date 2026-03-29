from pathlib import Path

imgs = list(Path(r"C:\Users\MASTER CORE\RescueVision\test_data\images").glob("*.jpg"))
print(f"Test images: {len(imgs)}")
imgs2 = list(
    Path(r"C:\Users\MASTER CORE\RescueVision\train_data\images\train").glob("*.jpg")
)
imgs3 = list(
    Path(r"C:\Users\MASTER CORE\RescueVision\train_data\images\val").glob("*.jpg")
)
print(f"Train images: {len(imgs2)}")
print(f"Val images: {len(imgs3)}")
