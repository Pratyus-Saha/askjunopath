import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "backend")
env_path = Path("backend/.env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from app.engines.prediction_career_engine import compute_career_prediction
from app.engines.prediction_finance_engine import compute_finance_prediction
from app.engines.prediction_relationship_engine import compute_relationship_prediction
from app.engines.dasha_engine import compute_dasha_from_chart
from app.synthesis.disclaimer import get_disclaimer
from app.synthesis.gemini_synthesizer import synthesize
from app.synthesis.payload_builder import build_payload
from app.synthesis.validator import validate

CHART = Path("frontend/src/fixtures/chart.sample.json")
OUT = Path("frontend/src/fixtures")
DOMAINS = {
    "career": compute_career_prediction,
    "finance": compute_finance_prediction,
    "relationship": compute_relationship_prediction,
}


def add_occupants(chart):
    houses = chart["houses"]
    planets = chart["planets"]
    cusps = [h["cusp_longitude"] for h in houses]

    def get_house(lon):
        for i in range(12):
            start = cusps[i]
            end = cusps[(i + 1) % 12]
            if start < end:
                if start <= lon < end:
                    return i
            else:
                if lon >= start or lon < end:
                    return i
        return 0

    occupant_map = {i: [] for i in range(12)}
    for planet in planets:
        idx = get_house(planet["longitude"])
        occupant_map[idx].append(planet["name"])

    for i, house in enumerate(houses):
        house["occupants"] = occupant_map[i]

    return chart


chart = json.loads(CHART.read_text())
chart = add_occupants(chart)

print("Occupants computed:")
for h in chart["houses"]:
    if h["occupants"]:
        print("  House " + str(h["house"]) + ": " + str(h["occupants"]))

as_of = datetime.now(timezone.utc)

# Generate synthesis fixtures
for domain, fn in DOMAINS.items():
    print("\nRunning " + domain)
    engine_output = fn(chart, as_of=as_of)
    payload = build_payload(engine_output)
    try:
        paragraphs = synthesize(payload, domain)
        validated = validate(paragraphs, payload, domain)
        synthesis = validated["paragraphs"]
        fallback_used = validated["fallback_used"]
        print(domain + " gemini ok fallback=" + str(fallback_used))
    except Exception as ex:
        print(domain + " gemini failed: " + str(ex))
        synthesis = [{"text": engine_output["summary"], "references": []}]
        fallback_used = True
    result = {
        "domain": domain,
        "engine_output": engine_output,
        "synthesis": synthesis,
        "fallback_used": fallback_used,
        "disclaimer": get_disclaimer(),
    }
    out = OUT / ("synthesis_" + domain + ".json")
    out.write_text(json.dumps(result, indent=2, default=str))
    print("Written " + str(out))

# Generate dasha timeline fixture
print("\nRunning dasha timeline")
timeline = compute_dasha_from_chart(chart)

# Convert dataclass to dict if needed
import dataclasses

def serialize_timeline(tl):
    def period_to_dict(p):
        return {
            "level": p.level,
            "lords": list(p.lords),
            "start": p.start.isoformat(),
            "end": p.end.isoformat(),
        }
    return {
        "birth": tl.birth.isoformat(),
        "birth_balance_lord": tl.birth_balance_lord,
        "birth_balance_years": tl.birth_balance_years,
        "mahadashas": [period_to_dict(p) for p in tl.mahadashas],
        "antardashas": [period_to_dict(p) for p in tl.antardashas],
        "pratyantardashas": [period_to_dict(p) for p in tl.pratyantardashas],
    }

timeline_dict = serialize_timeline(timeline)
dasha_out = OUT / "dasha_timeline.json"
dasha_out.write_text(json.dumps(timeline_dict, indent=2, default=str))
print("Written " + str(dasha_out))

print("\nAll done")