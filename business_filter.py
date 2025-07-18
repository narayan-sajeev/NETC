"""
Business filtering utilities for identifying truck-relevant businesses.
"""

import re

import pandas as pd
from tqdm import tqdm

# Threshold for info confidence
CONFIDENCE_THRESHOLD = 0.9

# Core patterns for truck-relevant businesses
TRUCK_KEYWORDS = [
    # Core freight and logistics
    "truck", "trucks", "trucking", "trailer", "trailers",
    "freight", "logistics", "transport", "transportation", "ltl",

    # Heavy-duty construction and related services
    "hauling", "haul", "excavation", "excavating",
    "construction", "grading", "sitework", "aggregates",
    "paving", "asphalt", "concrete",

    # Fleet maintenance / repair services
    "diesel", "repair", "tow", "towing", "tows",

    # Commercial rental and equipment providers
    "equipment", "rental"
]

# Exclusions (false positives and small contractors)
EXCLUDE_KEYWORDS = [
    # Residential & consumer services
    "accessories", "apartment", "bank", "budget", "car", "care", "cellphone", "cellphones",
    "cleaners", "cleaning", "furniture", "homes", "home", "hospital", "ice",
    "jewelry", "luxury", "mattress", "moving", "party", "phone", "phones", "piano",
    "pianos", "plumber", "restaurant", "rug", "rugs", "rv", "salon", "school",
    "shoe", "shoes", "storage", "vacation", "watch", "watches",

    # Musical instrument / non-fleet commercial
    "eyeglass", "eyeglasses", "woodwind", "woodwinds",

    # Auto/consumer repair & parts chains
    "advance", "auto", "autozone", "automotive", "body", "collision", "computer",
    "detailing", "firestone", "ford", "glass", "mazda", "medical", "motor", "motors",
    "napa", "oreilly", "penske", "shop", "tire", "tools", "toyota", "wash",

    # Local and non-commercial government
    "church", "city of", "county", "department", "park", "town", "town of", "township",
    "tower", "towne",

    # Generic consultants / irrelevant businesses
    "consultants", "credit", "dream", "electrician", "emissions", "event", "handyman",
    "hvac", "pc", "training", "wireless",

    # High-volume brand noise
    "fedex", "harbor", "saia"
]


def is_truck_relevant(name):
    """Check if business name indicates truck relevance."""
    if not isinstance(name, str) or not name:
        return False

    name_lower = name.lower()

    # Quick exclusion check
    if any(exclude in name_lower for exclude in EXCLUDE_KEYWORDS):
        return False

    # Check for truck keywords
    return any(keyword in name_lower for keyword in TRUCK_KEYWORDS)


def filter_truck_businesses(df):
    """Filter DataFrame for truck-relevant US businesses."""
    print("Filtering businesses...")

    # Confidence threshold - do this first to reduce dataset size
    initial_count = len(df)
    df = df[df["confidence"] >= CONFIDENCE_THRESHOLD]
    print(f"  Filtered by confidence: {initial_count:,} → {len(df):,}")

    # Filter by business name with progress bar - process in chunks for memory efficiency
    print("  Checking business names for truck relevance...")
    chunk_size = 10000
    mask_parts = []

    for start in tqdm(range(0, len(df), chunk_size), desc="Processing chunks"):
        end = min(start + chunk_size, len(df))
        chunk = df.iloc[start:end]
        chunk_mask = chunk["business_name"].apply(is_truck_relevant)
        mask_parts.append(chunk_mask)

    mask = pd.concat(mask_parts)
    df = df[mask].copy()
    print(f"  Filtered by business type: {len(mask):,} → {len(df):,}")

    # Filter out Canadian businesses
    if "addresses" in df.columns and len(df) > 0:
        print("  Filtering for US businesses...")
        chunk_size = 5000
        us_mask_parts = []

        for start in tqdm(range(0, len(df), chunk_size), desc="Checking addresses"):
            end = min(start + chunk_size, len(df))
            chunk = df.iloc[start:end]
            chunk_mask = chunk["addresses"].apply(
                lambda x: x[0]["country"] == "US" if x else True
            )
            us_mask_parts.append(chunk_mask)

        us_mask = pd.concat(us_mask_parts)
        df = df[us_mask]
        print(f"  Filtered by country: {len(us_mask):,} → {len(df):,}")

    # Force garbage collection
    import gc
    gc.collect()

    return df


def clean_name(name):
    if not isinstance(name, str):
        return None

    # Basic cleaning
    name = re.sub(r'["\']', '', name)  # Remove quotes
    name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
    name = name.strip()

    # Title case unless already uppercase
    return name if name.isupper() else name.title()


def clean_business_names(df):
    """Clean business names in DataFrame."""
    print("Cleaning business names...")

    # Process in chunks for memory efficiency
    chunk_size = 10000
    cleaned_parts = []

    for start in tqdm(range(0, len(df), chunk_size), desc="Cleaning names"):
        end = min(start + chunk_size, len(df))
        chunk = df.iloc[start:end].copy()
        chunk["business_name"] = chunk["business_name"].apply(clean_name)
        cleaned_parts.append(chunk)

    # Combine chunks
    df = pd.concat(cleaned_parts, ignore_index=True)

    # Remove empty names
    return df[df["business_name"].notna() & (df["business_name"] != "")]


def normalize_for_matching(name):
    """Normalize name for fuzzy matching comparisons."""
    if not name:
        return ""

    # Lowercase and remove business suffixes
    name = name.lower().strip()

    # Common suffixes to remove
    for suffix in [' llc', ' inc', ' corp', ' ltd', ' co']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]

    # Remove punctuation and normalize whitespace
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()

    return name
