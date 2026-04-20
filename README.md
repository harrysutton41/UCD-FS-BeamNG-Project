# UCD Formula Student BeamNG Model and Testing Workflow

This project is a BeamNG.tech and Python-based workflow for building, testing, and analysing a digital model of a Formula Student vehicle. The model was developed to assess whether BeamNG, together with BeamNGpy, can be used as a practical engineering tool for vehicle setup studies, repeatable simulation, telemetry logging, and comparative analysis.

Developed by Harry Sutton as part of a Master’s thesis at University College Dublin.

This repo contains the custom vehicle JBeam files, supporting BeamNG vehicle files, and Python scripts used to create a working UCD Formula Student car model, record a reference path, run repeatable waypoint-based tests, log telemetry, and export data for later analysis. The current workflow includes a reference-path recorder and a main BeamNGpy test script for automated configuration comparison on the ETK Driver Experience Centre route.

## Key Features

- Custom Formula Student BeamNG vehicle built from modular JBeam subsystem files
- Reference-path recording for repeatable path-based comparisons
- Automated waypoint-based testing using BeamNGpy
- Live telemetry plotting and CSV export
- IMU-based logging of longitudinal, lateral, and vertical vehicle response
- Path overlay and summary table generation for multiple saved configurations
- Parameter-based setup comparison workflow for suspension, damping, braking, anti-roll settings, and motor torque studies

## Limitations

- Requires BeamNG.tech and a working local mod installation
- Python scripts currently use hard-coded local file paths and may need editing before use
- Saved configurations and reference path files must exist in the expected locations
- The model is intended as a comparative engineering workflow, not as a fully validated digital twin of the physical car

## Folder Setup

Place the vehicle files inside your BeamNG mod folder:

`...\BeamNG.tech\current\mods\unpacked\test1\vehicles\test1\`

This folder should contain the main vehicle and subsystem files, including the chassis/body, suspension, hubs, brakes, engine, material definitions, and supporting info files. The current workflow uses a `test1` vehicle folder structure.

## How to Use

1. Install BeamNG.tech and the required Python packages.
2. Place the vehicle files in the BeamNG mod folder.
3. Update `BEAMNG_HOME` and `USER_HOME` in the Python scripts to match your machine.
4. Run `Ref_path_collector.py` to generate and save a reference path.
5. Run `ETK_DEC_Testfile.py` to load configurations, drive the route, record telemetry, and export results.

## Dependencies

- Python 3.x
- BeamNG.tech v0.37.6
- BeamNGpy v1.34.1
- NumPy
- Matplotlib
- Pandas

## Contact

harrysutton41@gmail.com

## Institution

University College Dublin

## Project

*The Development and Evaluation of a Digital Model for a Formula Student Vehicle in BeamNG with Python & BeamNGpy* (2026)
