"""Shared configuration for the ingestion pipeline."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    _ROOT = Path(__file__).resolve().parent.parent
    load_dotenv(_ROOT / ".env")
except ImportError:  # pragma: no cover
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = Path(os.getenv("INGEST_DOCUMENTS_DIR", PROJECT_ROOT / "data" / "documents"))
MANIFEST_PATH = Path(os.getenv("INGEST_MANIFEST_PATH", PROJECT_ROOT / "data" / "manifest.csv"))

HF_API_KEY = os.getenv("HF_API_KEY", "")
# Online-only embeddings: all-MiniLM-L6-v2 served via the HF Inference API.
HF_INFERENCE_URL = os.getenv(
    "HF_INFERENCE_URL",
    "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction",
)
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "32"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

CHUNK_TARGET_CHARS = int(os.getenv("CHUNK_TARGET_CHARS", "1200"))
CHUNK_OVERLAP_CHARS = int(os.getenv("CHUNK_OVERLAP_CHARS", "150"))

# Canonical scheme names -> folder aliases
SCHEME_ALIASES = {
    "HDFC FlexiCap Fund": ["flexi cap", "flexicap", "hdfc flexi"],
    "HDFC Small Cap Fund": ["small cap", "smallcap", "hdfc small"],
    "HDFC Large and Mid Cap Fund": ["large and mid cap", "large & mid cap", "large-mid", "hdfc large and mid"],
    "HDFC Index Fund - Nifty 50 Plan": ["nifty 50 index", "nifty50 index", "index fund - nifty 50", "hdfc nifty 50"],
    "HDFC ELSS Tax Saver Fund": ["elss tax saver", "elss", "taxsaver", "hdfc elss"],
}

ORG_ALIASES = {
    "SEBI": ["sebi"],
    "AMFI": ["amfi"],
    "Groww": ["groww"],
}

DEFAULT_SOURCE_URLS = {
    "HDFC FlexiCap Fund": "https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap",
    "HDFC Small Cap Fund": "https://www.hdfcfund.com/explore/mutual-funds/hdfc-small-cap",
    "HDFC Large and Mid Cap Fund": "https://www.hdfcfund.com/explore/mutual-funds/hdfc-large-and-mid-cap",
    "HDFC Index Fund - Nifty 50 Plan": "https://www.hdfcfund.com/explore/mutual-funds/hdfc-nifty-50-index-fund",
    "HDFC ELSS Tax Saver Fund": "https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver",
    "SEBI": "https://www.sebi.gov.in",
    "AMFI": "https://www.amfiindia.com",
    "Groww": "https://www.groww.in",
}


def detect_scheme(text: str) -> str:
    low = text.lower()
    for canonical, aliases in SCHEME_ALIASES.items():
        for alias in aliases:
            if alias in low:
                return canonical
    return ""


def detect_organization(text: str) -> str:
    low = text.lower()
    for canonical, aliases in ORG_ALIASES.items():
        if any(a in low for a in aliases):
            return canonical
    return "HDFC Mutual Fund"


def detect_document_type(name_or_text: str) -> str:
    low = name_or_text.lower()
    rules = [
        ("sid", "SID"),
        ("kim", "KIM"),
        ("fund facts", "FACTSHEET"),
        ("factsheet", "FACTSHEET"),
        ("leaflet", "LEAFLET"),
        ("presentation", "PRESENTATION"),
        ("latestnav", "NAV_DATA"),
        ("nav report", "NAV_DATA"),
        ("average aum", "AUM_DATA"),
        ("aum", "AUM_DATA"),
        ("faq", "FAQ_DATASET"),
        ("ter", "TER_DATA"),
        ("total expense", "TER_DATA"),
        ("addendum", "ADDENDUM"),
        ("form", "FORM"),
    ]
    for needle, dtype in rules:
        if needle in low:
            return dtype
    return "OTHER"
