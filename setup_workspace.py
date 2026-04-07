import os
import shutil

# Paths
BASE_PATH = os.getcwd()
WORKSPACE_PATH = os.path.join(BASE_PATH, 'Tensorflow', 'workspace', 'images')
HASHED_IMAGES_DIR = os.path.join(BASE_PATH, 'images for phrases')

# Create Directories
paths = {
    'WORKSPACE_PATH': os.path.join('Tensorflow', 'workspace'),
    'SCRIPTS_PATH': os.path.join('Tensorflow','scripts'),
    'APIMODEL_PATH': os.path.join('Tensorflow','models'),
    'ANNOTATION_PATH': os.path.join('Tensorflow', 'workspace','annotations'),
    'IMAGE_PATH': WORKSPACE_PATH,
    'TRAIN_PATH': os.path.join(WORKSPACE_PATH, 'train'),
    'TEST_PATH': os.path.join(WORKSPACE_PATH, 'test'),
}

for path in paths.values():
    if not os.path.exists(path):
        os.makedirs(path)

print("✅ Workspace directories created.")

# Helper to copy images if user wants
print(f"ℹ️ Found 'images for phrases' at: {HASHED_IMAGES_DIR}")
print("   Run this script with --copy to import them into the workspace.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--copy', action='store_true', help='Copy images from "images for phrases" to workspace')
    args = parser.parse_args()

    if args.copy and os.path.exists(HASHED_IMAGES_DIR):
        print("📂 Copying images...")
        # Simple copy logic: moving all subfolders to 'collectedimages' equivalent
        dest_dir = os.path.join(paths['IMAGE_PATH'], 'collectedimages')
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            
        # Iterate and copy
        for item in os.listdir(HASHED_IMAGES_DIR):
            s = os.path.join(HASHED_IMAGES_DIR, item)
            d = os.path.join(dest_dir, item)
            if os.path.isdir(s):
                if not os.path.exists(d):
                    shutil.copytree(s, d)
                    print(f"   Copied {item}")
                else:
                    print(f"   Skipped {item} (already exists)")
        
        print("✅ Images copied. You can now run labelImg.")
