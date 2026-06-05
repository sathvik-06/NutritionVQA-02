import inspect
try:
    from paddleocr import PaddleOCR
    print(f"PaddleOCR signature: {inspect.signature(PaddleOCR)}")
except Exception as e:
    print(f"Error: {e}")
