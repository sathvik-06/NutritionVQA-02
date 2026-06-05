try:
    from mistralai.client import Mistral
    print("Import Mistral from mistralai.client success")
except Exception as e:
    print(f"Import Mistral from mistralai.client failed: {e}")

try:
    from mistralai import Mistral
    print("Import Mistral from mistralai success")
except Exception as e:
    print(f"Import Mistral from mistralai failed: {e}")

try:
    from mistralai.client.models import UserMessage
    print("Import UserMessage from mistralai.client.models success")
except Exception as e:
    print(f"Import UserMessage from mistralai.client.models failed: {e}")

try:
    from mistralai.models import UserMessage
    print("Import UserMessage from mistralai.models success")
except Exception as e:
    print(f"Import UserMessage from mistralai.models failed: {e}")
