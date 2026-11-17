import re
from difflib import SequenceMatcher

def normalize_title(title: str) -> str:
    # Remove punctuation, lowercase, normalize spaces
    t = re.sub(r"[^\w\s]", " ", title.lower())
    # Remove common filler words
    t = re.sub(r"\b(application|for|degree|intake|programmes?|courses?|offered|by)\b", " ", t)
    return " ".join(t.split())

def is_duplicate(candidate_title: str, existing_titles: list) -> tuple:
    c_norm = normalize_title(candidate_title)
    c_words = set(c_norm.split())
    # Extract year if present
    c_year = re.search(r"\b(202\d)\b", candidate_title)
    c_year_val = c_year.group(1) if c_year else None

    for ext in existing_titles:
        e_norm = normalize_title(ext)
        e_words = set(e_norm.split())
        e_year = re.search(r"\b(202\d)\b", ext)
        e_year_val = e_year.group(1) if e_year else None

        # Check year match: if both have years and they differ, probably different intake
        if c_year_val and e_year_val and c_year_val != e_year_val:
            continue

        # Overlap of meaningful keywords (words >= 4 chars)
        meaningful_c = {w for w in c_words if len(w) >= 4}
        meaningful_e = {w for w in e_words if len(w) >= 4}
        if not meaningful_c:
            continue

        intersection = meaningful_c.intersection(meaningful_e)
        ratio = len(intersection) / len(meaningful_c)

        # High keyword overlap AND high overall similarity
        sim = SequenceMatcher(None, c_norm, e_norm).ratio()

        if ratio >= 0.75 or (ratio >= 0.60 and sim >= 0.65):
            return True, ext

    return False, None

# Test with our real titles
import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build("blogger", "v3", credentials=c)
res = s.posts().list(blogId="3109655798381913489", maxResults=50, fetchBodies=False).execute()
lkuni_titles = [p["title"] for p in res.get("items", [])]

test_candidates = [
    "Ocean University External Degree Programs Application 2027",
    "Agro Technology Degree Intake 2026 – University of Colombo (UCIARS)",
    "Business Administration (BBA) External Degree 2026 – University of Peradeniya",
    "Radiographer Graduate Recruitment 2026 – Ministry of Health",
    "Archaeology Postgraduate Courses 2026 – PGIAR, University of Kelaniya",
    "Sign Language Courses 2026 – National Institute of Education (NIE)",
    "MSc in Data Science 2027 – Open University (OUSL)",
    "Nursing Graduate Recruitment 2026 – Ministry of Health"
]

print("DUPLICATE DETECTION RESULTS:")
for cand in test_candidates:
    dup, matched_title = is_duplicate(cand, lkuni_titles)
    if dup:
        print(f"❌ DUPLICATE: '{cand}' -> Matches '{matched_title}'")
    else:
        print(f"✅ NEW POST: '{cand}'")
