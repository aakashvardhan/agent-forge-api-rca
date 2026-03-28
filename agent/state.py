import os
from dotenv import load_dotenv

load_dotenv()

THRESHOLD_K: float = float(os.getenv("THRESHOLD_K", "2.5"))
