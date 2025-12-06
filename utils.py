# utils.py
import json

def safe_json_load(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None
