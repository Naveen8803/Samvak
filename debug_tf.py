
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

try:
    import tensorflow as tf
    print(f"TensorFlow Version: {tf.__version__}")
    try:
        from tensorflow import keras
        print("Success: from tensorflow import keras")
    except ImportError as e:
        print(f"Failed: from tensorflow import keras ({e})")

    try:
        import keras
        print(f"Keras Version: {keras.__version__}")
    except ImportError:
        print("Failed: import keras")

    try:
        from tensorflow.keras.utils import to_categorical
        print("Success: from tensorflow.keras.utils import to_categorical")
    except ImportError as e:
        print(f"Failed: from tensorflow.keras.utils import to_categorical ({e})")

except ImportError as e:
    print(f"Failed to import tensorflow: {e}")
