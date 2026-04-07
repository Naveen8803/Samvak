
print("Importing tensorflowjs...")
try:
    import tensorflowjs as tfjs
    print("Success: import tensorflowjs")
except Exception as e:
    print(f"Failed: import tensorflowjs ({e})")
    import traceback
    traceback.print_exc()
