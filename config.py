import os

# Base directory relative to this config file
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Data Paths
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_INPUT = os.path.join(DATA_DIR, "test_files")
DEFAULT_OUTPUT = os.path.join(DATA_DIR, "output")
SUSPICIOUS_FOLDER = os.path.join(DATA_DIR, "suspicious")

# Memory Cache
MEMORY_FILE = os.path.join(DATA_DIR, "processed_memory.json")

# Models Paths
MODEL_DIR = os.path.join(DATA_DIR, "models")

# Legacy LSTM paths (kept for reference)
MODEL_PATH = os.path.join(MODEL_DIR, "dl_categorizer.keras")
TOKENIZER_PATH = os.path.join(MODEL_DIR, "dl_tokenizer.pkl")
LABEL_ENCODER_PATH = os.path.join(MODEL_DIR, "dl_label_encoder.pkl")

# Transformer Classifier paths
TRANSFORMER_CLASSIFIER_PATH = os.path.join(MODEL_DIR, "transformer_classifier.pkl")
TRANSFORMER_LABEL_ENCODER_PATH = os.path.join(MODEL_DIR, "transformer_label_encoder.pkl")

# Security Extensions
DANGEROUS_EXT = {".exe", ".bat", ".cmd", ".js", ".vbs", ".msi", ".scr", ".pif", ".ps1"}
SAFE_EXT = {".docx", ".xlsx", ".pdf", ".txt", ".jpg", ".png", ".mp4"}

# Renamer Stop Words
# Renamer Stop Words - common filler words that add no meaning to a filename
STOP_WORDS = {"this", "is", "a", "an", "the", "appears", "to", "be", "of", "for", "and", "in", "on", "with", "it", "that", "there", "some", "here", "are"}