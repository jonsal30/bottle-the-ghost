# Cloud in a Bottle — v1.2.1 Truth Mode

A local-first personal data laboratory.

## Quick start

```bash
python3 MASTER_BUILD.py
cd cloud-in-a-bottle
./run.sh
```

Dashboard: `http://127.0.0.1:8765/lab_dashboard.html?godmode=1`

Offline map: `http://127.0.0.1:8765/map.html?godmode=1`

## Truth-mode guarantees

- Scans only `./exports/`.
- Normal runs never fabricate records.
- `python3 lab.py --demo` is the only demo-data path, and only activates when no real events were found.
- Web server binds only to `127.0.0.1`.
- No runtime CDN dependencies.
- Normalized events preserve `source_file` and `source_index` provenance.
- Imported text is rendered with DOM `textContent`, not trusted HTML.
- Location data renders in a fully offline coordinate map with no remote tiles.

## Generated data

`data/events.jsonl`, `advertisers.json`, `logins.json`, `apps.json`, `locations.json`, `parse_errors.json`, and `manifest.json`.

## God Mode

Add `?godmode=1` to the dashboard URL. Relationship-decay output is explicitly a frequency/recency heuristic, not a judgment about a relationship.

## Airgap

`lab_v1_2_airgap.py` validates that generated pages contain no remote runtime asset references.

## v1.3 direction

A local model can sit over the normalized store. Its answers should separate evidence from inference and point back to source records.