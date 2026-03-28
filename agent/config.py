import os
from dotenv import load_dotenv

load_dotenv()

DIGITALOCEAN_ACCESS_TOKEN = os.environ.get("DIGITALOCEAN_ACCESS_TOKEN", "")
GRADIENT_MODEL_ACCESS_KEY = os.environ.get("GRADIENT_MODEL_ACCESS_KEY", "")
MODEL_NAME = os.environ.get("GRADIENT_MODEL", "llama3.3-70b-instruct")
THRESHOLD_K = float(os.environ.get("THRESHOLD_K", "2.5"))
