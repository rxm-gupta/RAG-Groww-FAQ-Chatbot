import requests
import time

BASE = "http://localhost:8000"
qs = [
    ("generic TER", "What is the expense ratio of HDFC FlexiCap Fund?"),
    ("Direct Plan TER", "What is the Total Expense Ratio (TER) of HDFC FlexiCap Fund under the Direct Plan?"),
    ("capital gains space", "How to download capital gains statement"),
    ("capital-gains hyphen", "How to download capital-gains statement"),
    ("riskometer", "What is the Risk-o-meter rating of HDFC Small Cap Fund?"),
    ("control exit load", "What is the exit load of HDFC Small Cap Fund?"),
]

for label, q in qs:
    try:
        d = requests.post(BASE + "/chat", json={"question": q, "session_id": "smoke-" + label}, timeout=120).json()
        src = d.get("source") or {}
        ans = d.get("answer", "")[:180].replace(chr(10), " ")
        if d.get("refused"):
            status = "REFUSED/" + str(d.get("refusal_type"))
        elif "couldn" in ans.lower():
            status = "NOT_FOUND"
        elif src.get("url"):
            status = "OK"
        else:
            status = "NO-SOURCE"
        print(f"{label}: {status} | intent={d.get('intent')} | {ans[:120]}")
        print(f"  src: {(src.get('title') or '')[:55]} | page {src.get('page')} | {str(src.get('url') or '')[:70]}")
        print(f"  last_updated: {d.get('last_updated')}")
    except Exception as e:
        print(label, "FAILED", e)
    time.sleep(0.5)
