import os
import shutil
import pandas as pd

# === Path Setup ===
project_dir = "."  # Assuming you're running this from inside CS6420_QRCode
csv_path = os.path.join(project_dir, "hands", "HandInfo.csv")
image_src_dir = os.path.join(project_dir, "hands", "hand_images")
output_dir = os.path.join(project_dir, "11k_hands_subset", "train")

# Make output folders
os.makedirs(os.path.join(output_dir, "male"), exist_ok=True)
os.makedirs(os.path.join(output_dir, "female"), exist_ok=True)

# Load CSV
df = pd.read_csv(csv_path)
df.columns = [c.strip().lower() for c in df.columns]  # Clean column names

# Copy images to gender folders
count = 0
for _, row in df.iterrows():
    filename = row['imagename'].strip()
    gender = row['gender'].strip().lower()

    src = os.path.join(image_src_dir, filename)
    dst = os.path.join(output_dir, gender, filename)

    if os.path.exists(src) and gender in ['male', 'female']:
        shutil.copy(src, dst)
        count += 1

print(f"✅ Copied {count} images into male/female folders.")
