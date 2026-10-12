# Floor-plan compliance checker (prototype)

Goal: read architectural drawings (AutoCAD-plotted PDFs now, DXF/DWG next), build a
space graph with real-world geometry, and check it against building rules (UDCPR,
Maharashtra) with every result traceable to a clause and to drawing elements.

The code is a working prototype written as a sequence of scripts. Treat it as a reference
implementation to refactor, not as a finished library.

## Repository layout

```
geom.py         PDF vector reading (PyMuPDF) -> shapely; subpaths(), as_polys(), as_lines()
seg.py          unit plan: floor hatch, wall poché, doors (arc + leaf -> hinge, threshold)
openings.py     doorless openings = facing wall-end pairs
rseg.py         raster room segmentation (floor minus barriers -> connected components)
rooms.py        room labels -> cells, scale fit from labelled dims, OBB, clear width
graph.py        networkx MultiGraph: spaces + EXT + LOBBY; door/opening/glazed_door/window/wall edges
graph_g.py      graph.py variant that keeps glazing geometry per room (GLAZ) for r9201.py
rules.py        builds the graph and writes floorplan_graph.json (no checks); prototype checks R1-R7
                (illustrative NBC-style thresholds, NOT configured rules) are printed to the terminal only
export_geom.py  adds metric coordinates (display orientation) to floorplan_graph.json
draw_graph.py   graph overlay on the plan, in the PDF's display orientation; marks spaces with a
                FAIL/REVIEW result in floorplan_checks.json
r9201.py        UDCPR 9.20.1 natural lighting; thresholds, room kinds and targets read from the rule
                record; writes floorplan_checks.json
viz.py          small matplotlib helpers
rules/
  rule_schema_v0.1.json  minimal JSON Schema for rule records (covers only the 10 UDCPR rules)
  primitives.json        registry of named measurements a rule may use (+ implemented flag)
  udcpr_rules_v1.json    the 10 rules as 13 records / 24 checks (all status: draft)
  validate_rules.py      schema validation + primitive/element cross-checks
inputs/         input drawings (not in the repo); default location for both pipelines
outputs/        everything the pipelines write: floorplan_graph.json/.png, floorplan_checks.json
                (unit plan), parking_P1_checks.json, parking_P1_check.png
parking/
  pk_base.py    parking PDF loading, display transform D(), scale S_M
  pk_check.py   bays (A-PARKING rectangles), drive aisle (tan fill on layer 0), clear width
                via distance transform + pruned skeleton, bay access test
  pk_viz.py     overlay image
  pk_report.py  writes parking_P1_checks.json: `checks` = provided rules only (8.1.1, 9.12.2);
                `observations` (drawing QA, not rules) are computed but hidden;
                set INCLUDE_OBSERVATIONS=1 to include them
```

Run (unit plan): `python rules.py`, then `python export_geom.py`, `python r9201.py`,
`python draw_graph.py` (draw_graph reads the checks file r9201 writes).
Run (parking): from `parking/`, `python pk_report.py`, then `python pk_viz.py`.
Inputs are not in the repo; put them in `inputs/`. Defaults (resolved relative to the repo, set
in `geom.py` / `parking/pk_base.py`): `inputs/2028.09.23_TOWER Q_UNIT PLANS-Model-5.pdf` and
`inputs/2026.09.23_TOWER Q - PARKING FLOOR PLANS-Model.pdf`; override with `FLOORPLAN_PDF` /
`PARKING_PDF`. All results are written to `outputs/` (`OUTPUTS` in `geom.py`), currently from
the Tower Q samples. `r9201.py` regenerates `graph_g.py` from `graph.py` on each run.

Dependencies: pymupdf, shapely, networkx, opencv-python, numpy, scipy, scikit-image,
matplotlib; ezdxf for the DXF port; LibreDWG (built from source) only if reading raw DWG.

## Pipeline (unit plans)

1. Read vector paths with their AutoCAD layer (PDF optional content groups). Room labels are
   NOT on any layer in these PDFs; attach them by position.
2. Elements by layer + fill colour: floor = A-HATCH light blue / tan; walls = black fills on
   A-HATCH and A-COLUMN HATCH (A-WALL-MAS is white masking, not walls); doors = arc + leaf on A_DOOR.
3. Door threshold: hinge is the corner candidate (E1.x,E2.y)/(E2.x,E1.y) nearest a leaf; the arc
   endpoint touching the leaf is the open position; threshold = hinge -> closed endpoint,
   extended 4 pt into the jambs.
4. Openings: wall-end edges 1.5-10 pt long, facing, coaxial, 6-45 pt apart.
5. Rooms: rasterise at 4 px/pt, draw barriers (walls, glazing, thresholds, openings), take
   4-connected components, trace back to polygons. Vector booleans leaked at door frames.
6. Scale: median of label_dim / OBB_dim over single-label near-rectangular rooms
   (0.0477 m/pt for Tower Q, ±2%). Clear width = 2 x max distance transform.
7. Graph edges by side-sampling across thresholds, openings and glazing; wall adjacency by
   buffered-polygon overlap. Glazing: room both sides -> glazed_door, one side -> window,
   toilet-toilet -> shaft ventilator; parallel sash lines merged per room pair.

## Conventions and decisions

- **Orientation.** PDFs carry /Rotate 270. Extract in unrotated page space; transform every
  exported or drawn coordinate with `page.rotation_matrix`. Exported JSON uses metres, display
  orientation, y up, origin documented in `coordinate_system`.
- **Scale.** Prefer, in order: title-block scale or scale bar, dimension entities, known
  elements (lift doors, lobby dimension), label fit. Do not calibrate on the elements a rule
  checks (the parking scale comes from the 2.76 m lobby dimension, not from bays).
- **Rule results** are PASS / FAIL / FLAG / REVIEW / CANNOT DETERMINE. Never report PASS when
  the input lacks the data; missing data is CANNOT DETERMINE.
- **Thresholds** in `rules.py` are illustrative. Real ones come from rule records.
- **Only provided rules go in `checks`.** "Provided" = a record in `rules/udcpr_rules_v1.json`;
  a checks file holds only configured records whose element type exists in that plan (unit plan:
  UDCPR-9.20.1 only). Anything else (legend vs drawing, bay access, level
  annotation consistency) goes in `observations`, labelled as not being a rule. Do not mix them. Observations are hidden by default
  (user decision); do not surface them unless asked.
- **Measured door width** is leaf width (swing radius), not clear opening.

## Rules architecture (agreed direction)

- Rules are data, not code: each clause -> a record with `pattern`, operands, applicability,
  exceptions, units, source clause (see `rules/udcpr_rules_v1.json`, schema v0.1).
- Schema v0.1 (minimal, to be improved): rule = id, clause, title, status (draft|reviewed),
  applies_to {element, kind, where}, applicability, checks[], exceptions[], requires_data[].
  Check patterns: threshold, ratio, max_distance, count, lookup_threshold, relation; optional
  `when` condition. Values: number, [short,long] pair, {factor, of: expr}, {by, values}.
  Exceptions with effect `unspecified` mean "known but not encoded" -> CANNOT DETERMINE.
  Lookup tables carry `complete`; out-of-range keys on incomplete tables -> CANNOT DETERMINE.
  One rule record selects one element type, so 8.1.1, 9.12.2 and 6.9 are split into two
  records each (13 records for 10 rules).
- Validate after any edit: `cd rules && python validate_rules.py`.
- Hand-code a small library of patterns (threshold, ratio, distance, required/prohibited
  relation, path, count/aggregate, table lookup, containment) and primitives (area, clear
  width, glazed area, shortest path, adjacency by edge type).
- An LLM extracts records from the regulation text; a schema validator rejects unknown
  primitives; a human reviews every record before it is used.
- A KG holds definitions (habitable room, carpet area), applicability, cross-references,
  exceptions, provenance and versions. Evaluation runs compiled records against the plan graph.
- Extract from the notified UDCPR text, not from summaries: the current 10-rule sheet drops
  conditions (e.g. full Table 9-C for 9.20.2, the 6.9 height-based area condition).

## Current results worth knowing

- Tower Q 4.5BHK unit: topology matches the drawing. 9.20.1 (floorplan_checks.json): opening
  ratio CANNOT DETERMINE for all rooms (no head/sill heights; required average opening height is
  reported); depth FAIL for Living/Foyer/Dining (10.5 m, 19% of floor >7.5 m from the deck
  glazing); Kitchen REVIEW on both checks - its only light is 1.00 m of glazing onto the Utility,
  which is not exterior/open_deck. Deck vs utility is told apart by name ("deck") until the kind
  taxonomy exists; Servant Room is checked because the lexicon maps it to bedroom. RERA polyline 205.3 m² vs stated 194.66 m².
- P1 parking: 64 bays (16 tandem) match the legend count, but all are drawn 2.5 x 5.0 m while
  the legend states 2.5 x 5.5 m (observation). Rule results: bays pass 8.1.1 at the limit;
  aisle 6.0 m typical, 3.58 m at the NE taper (pass); west exit ramp 3.63 m wide (pass); ramp
  slope pass on annotation only; 2W bays and ramp count cannot be determined. Observations:
  8 bays have no detected aisle frontage (reported with measured gap only); level tags are
  inconsistent. Ramp slope needs sections or P2/P3 plans.

## Known weaknesses / next work

1. Refactor: replace `exec(open(...))` chaining with modules and one `build_graph(path, config)`
   entry point; move layer names, fill colours, pt tolerances, kind lexicon and thresholds into
   a config. Express tolerances in metres after scale is known.
2. Stable node IDs (label-based, centroid-based for unlabelled), so revisions can be diffed.
3. DXF front end (ezdxf, model space in mm): check `$INSUNITS` and sanity-check a door
   (~900 mm); explode blocks with full transforms; doors from block inserts.
4. Graph levels above rooms: building -> storey -> space, with heights (needed by 6.9,
   9.12.2, 9.20.2, 9.27.1). New element types: shaft, chowk, ramp, stair flight, parking bay,
   2W zone, drive aisle.
5. Window/door head and sill heights (elevations, or an explicit assumed-value flag) to turn
   9.20.1 opening area into PASS/FAIL.
6. Open-plan zones with several labels: split by function (geodesic Voronoi around labels)
   when rules apply per function.
7. Parking: 2W zones as elements; multi-level ramp graph from sections (9.12.2 slope, count).
   Bay-access analysis (bay-to-bay adjacency, parallel bays, swept paths) only if it becomes a
   rule in the rule base.
8. Rule engine: evaluator that loads rules/udcpr_rules_v1.json, selects elements, computes
   primitives from primitives.json, emits PASS/FAIL/NOT APPLICABLE/CANNOT DETERMINE with clause
   id; then port r9201.py and parking checks to it. Schema to improve: clause-text provenance
   per check, units on all values, structured definitions (habitable room), versions/editions,
   multi-element relations, KG for definitions and applicability.
9. Room-kind mapping: replace the keyword lexicon with a normalisation step (lexicon + LLM)
   to a fixed taxonomy; servant room / store / puja need explicit regulatory decisions.

## Sample inputs used

- `2028_09_23_TOWER_Q_UNIT_PLANS-Model-5.pdf` (unit plan, 42 layers)
- `2026.09.23_TOWER_Q_-_PARKING_FLOOR_PLANS-Model.pdf` (P1 at +554.10)
- `2026_07_06_Master_Plan (1).dwg` (site master plan, AC1032, mm units; converted with LibreDWG)
- `UDCPR_10_easy_to_miss_rules.xlsx` (rule summaries)
