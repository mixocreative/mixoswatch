# icc/ — drop your CMYK ICC profiles here

This folder is `.gitignore`d. ICC profile binaries are not redistributable
under Adobe / ECI / Fogra / Mimaki licenses, so the repository does not
carry them.

To wire up the tools, place one or more `.icc` / `.icm` CMYK profiles into
this folder, then run:

```
python scripts/gen_luts.py
python scripts/gen_libraries.py
```

The build step will:
- detect each profile, skip anything that is not a CMYK destination,
- write a forward lookup table to `data/luts/<name>.lut`,
- write a reverse lookup table to `data/luts/<name>.rcmyk.lut`,
- write a curated print-safe library to `data/libraries/<name>.json`,
- update `data/luts/index.json` and `data/libraries/library_index.json`.

## Recommended starter profiles (all free)

- `CoatedFOGRA39.icc` — Adobe ICC Profiles bundle
- `ISOcoated_v2_eci.icc` — eci.org
- `JapanColor2001Coated.icc` — Adobe ICC Profiles bundle
- `USWebCoatedSWOP.icc` — Adobe ICC Profiles bundle

See the top-level `README.md` for direct links.
