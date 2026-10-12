# Floor-plan compliance checker (prototype)

Start with CLAUDE.md: it describes the pipeline, decisions, current results and next work.

Inputs are not included. Put them in `inputs/`; the scripts look there by default:
- unit plan PDF  -> `inputs/2028.09.23_TOWER Q_UNIT PLANS-Model-5.pdf`
- parking PDF    -> `inputs/2026.09.23_TOWER Q - PARKING FLOOR PLANS-Model.pdf`

To use another file, set FLOORPLAN_PDF=<path> or PARKING_PDF=<path>.

Unit plan:  python rules.py && python export_geom.py && python r9201.py && python draw_graph.py
Parking:    cd parking && python pk_report.py && python pk_viz.py
Rules:      cd rules && python validate_rules.py

All results (JSON and images) are written to outputs/.
