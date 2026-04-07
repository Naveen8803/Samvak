
import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

DATA_FILE = "data.pickle"
MODEL_FILE = "model.p"

def train_model():
    print("🚀 Training Machine Learning Model...")
    
    # 1. Load Data
    try:
        with open(DATA_FILE, 'rb') as f:
            data_dict = pickle.load(f)
    except FileNotFoundError:
        print(f"❌ Data file '{DATA_FILE}' not found. Please run 'collect_training_data.py' first.")
        return

    data = np.asarray(data_dict['data'])
    labels = np.asarray(data_dict['labels'])
    
    # Check if data is empty
    if len(data) == 0:
        print("❌ No data found in 'data.pickle'.")
        return

    print(f"✅ Loaded {len(data)} samples from {len(set(labels))} classes: {set(labels)}")

    # 2. Split Data
    x_train, x_test, y_train, y_test = train_test_split(data, labels, test_size=0.2, shuffle=True, stratify=labels)

    # 3. Train Classifier
    print("🧠 Training Random Forest Classifier...")
    model = RandomForestClassifier()
    model.fit(x_train, y_train)

    # 4. Evaluate
    y_predict = model.predict(x_test)
    score = accuracy_score(y_predict, y_test)
    print(f"🏆 Model Accuracy: {score * 100:.2f}%")

    # 5. Save Model
    with open(MODEL_FILE, 'wb') as f:
        pickle.dump({'model': model}, f)
    
    print(f"💾 Model saved to '{MODEL_FILE}'!")

if __name__ == "__main__":
    train_model()
