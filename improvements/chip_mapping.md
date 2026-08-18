# Chip Mapping & Move-to-Device — Improvement To-Do List

Findings from a code review of `LabExT/Movement/{Transformations,Calibration,MoverNew,PathPlanning}.py`,
`LabExT/Wafer/*` (chip/device data + import), and their GUI (`LabExT/View/Movement/*`),
prompted by two questions: (1) can chip-mapping accuracy improve automatically by
feeding peak-search results back in while measurements run, and (2) how does the
existing "calibrate to 3 devices" workflow actually work — is it triangulation?

## How this works today (reference)

### Chip device data
- `Device` (`LabExT/Wafer/Device.py:14-58`) is a **frozen** dataclass — `id`,
  `type`, `in_position`, `out_position`. Once imported, a device's designed position
  can't be mutated in place, only replaced via a fresh import.
- `Chip` (`LabExT/Wafer/Chip.py:16-89`) holds all devices keyed by ID and is
  auto-dumped to `last_imported_chip.json` for reload on next launch.
- Two real importers, both plugin-based (`LabExT/Wafer/ChipSourceAPI/`): `PhoenixPhotonics`
  (comma-delimited CSV, `LabExT/Wafer/ChipSources/PhoenixPhotonics.py`) and
  `IBMMaskDescription` (JSON, `LabExT/Wafer/ChipSources/IBMMaskDescription.py`). Neither
  reads `.gds` directly.
- GDS import is instead handled by an ad-hoc notebook, `configs/gds_file_markup.ipynb`,
  which reads a real `.gds` file via `gdstk` and writes out `IBMMaskDescription`-schema
  JSON. See "Chip-mapping data quality" below — it has two live inconsistencies.
- Importing a chip resets any existing point-pairing calibration for every stage
  (`MoverNew.set_chip`, `LabExT/Movement/MoverNew.py:142-159`), since pairings reference
  `Device` objects belonging to the old chip.

### Calibration is a Kabsch rigid-body fit, not triangulation
Three transform tiers, composed (not subclassed) inside `Calibration`
(`LabExT/Movement/Calibration.py:81`), selected by a `State` enum
(`LabExT/Movement/config.py:66-95`):

1. **`AxesRotation`** (`LabExT/Movement/Transformations.py:296-472`) — a signed
   permutation matrix (nearest-90°, no arbitrary angle, no scale). Requires exactly 3
   axis mappings, set once via a dropdown + "wiggle axis" test in the Calibration
   Wizard — no least-squares fit involved.
2. **`SinglePointOffset`** (`Transformations.py:475-646`) — needs exactly 1
   stage↔chip point pair. `update()` (`:570-589`) always **overwrites** the previous
   offset; extra points don't accumulate or improve anything at this tier. Its own
   docstring (`:487`) flags it as an approximation: *"assumes that the stage and chip
   axes are parallel. This is not the case in reality."*
3. **`KabschRotation`** (`Transformations.py:649-1013`) — a real rigid-body
   (rotation + translation, no scale) **least-squares** fit via SVD, `MIN_POINTS = 3`
   (`:658`) as a **floor, not a ceiling** — `is_valid` (`:743-747`) only checks
   `len(self.pairings) >= self.MIN_POINTS`. `update()` (`:786-845`) re-solves the full
   fit over *every* accumulated pairing each time a new one is added, via
   `rigid_transform_with_orientation_preservation` (`:1015-1103`, a
   Kabsch/Umeyama-style SVD alignment). Duplicate pairings from the same device are
   rejected unless `replace_existing=True` is passed (added for auto-refinement,
   see below), so each extra point must otherwise come from a distinct device.

**Direct answer to "does triangulation work":** there's no literal triangulation
(no angle/distance-based position solving) — it's a Kabsch/SVD rigid alignment fit.
It **does already support more than 3 points as a genuine over-determined
refinement**, not a special mode — confirmed by an existing test,
`test_transformation_estimates_fourth_variable`
(`LabExT/Tests/Movement/Transformations_test.py:603-624`), which fits on 3 of 4 real
recorded calibration points (`vacherin.json` fixture) and asserts the held-out 4th is
predicted correctly. The GUI's own hint text ("*Please define for each stage at least
three points to calibrate the stages globally*",
`LabExT/View/Movement/MovementWizard.py:1167`) confirms "3" was always meant as a
minimum, not a target.

**Known gaps:** no scale/affine transform tier exists anywhere (only rotation +
translation). *(Originally also: no RMSD/fit-residual anywhere in the app, leaving
`KabschRotation.get_z_plane_angles()` at `Transformations.py:847-871` — a plane-tilt
sanity check, not a residual — as the only quality-adjacent number. That gap is now
closed; see "Calibration quality visibility" below.)*

### Move-to-device call chain
`MoveStagesDeviceWindow.execute_movement()`
(`LabExT/View/Movement/MoveStagesDeviceWindow.py:91-107`) →
`MoverNew.move_to_device()` (`LabExT/Movement/MoverNew.py:736-765`, builds a target
per stage orientation from `device.input_coordinate`/`output_coordinate`) →
`MoverNew.move_absolute()` (`:598-679`, path planning + per-waypoint moves) →
`Calibration.move_absolute()` (`LabExT/Movement/Calibration.py:642-676`) →
`transform_chip_to_stage_coordinate()` (`:502-530`, dispatches to Kabsch or
single-point-offset per the state above) → concrete stage driver
(`ThorlabsKCube.move_absolute`, `LabExT/Movement/Stages/ThorlabsKCube.py:352-374`).
The same `move_to_device` is also invoked automatically per-device inside a batch
sweep by `StandardExperiment` when enabled (see below).

### Peak search feeding back into calibration
`PeakSearcher`/`EdgeSearcher` themselves operate purely in stage coordinates and have
**zero** references to `Calibration`/`Transformation` in either file — that separation
was kept deliberately (see "Feedback-loop integration boundaries" below).
`StandardExperiment.py:272-282` does the per-device work in a sweep:
```
if self.exctrl_auto_move_stages: self._mover.move_to_device(self._chip, device)   # :272-273
if self.exctrl_enable_sfp:       data["search for peak"] = self._peak_searcher.search_for_peak()   # :277-279
```
(flags default to `False`, set at `StandardExperiment.py:112-113`.)

*Originally* the peak-search result was only ever written into that device's own
measurement JSON, and the **only** path by which an improved position could reach the
calibration was fully manual: a human reopens `CoordinatePairingsWindow` (which has a
"Perform Search for Peak..." shortcut, purely for convenience) and clicks "Save and
Close", which snapshots the current position as a new pairing and calls
`calibration.update_single_point_offset(p)` / `update_kabsch_rotation(p)`
(`MovementWizard.py:1317,1319`, inside `CoordinatePairingStep._save_coordinate_pairing`,
`:1311-1322`).

That manual path still exists and is unchanged. In addition, an **opt-in automatic
path** now exists — see "Auto-refine calibration from peak-search results" below.

---

## Improvement ideas

### Auto-refine calibration from peak-search results during measurement (the core idea)
- [x] Wired into `StandardExperiment`: after a successful `search_for_peak()`, the new
      `_refine_calibration_from_sfp()` (`StandardExperiment.py:403-492`) builds a
      `CoordinatePairing` per stage from the device's designed chip coordinate
      (`device.input_coordinate`/`output_coordinate`, matching how `move_to_device`
      picks targets) plus the post-search actual stage position read in
      `CoordinateSystem.STAGE`, and calls `calibration.update_kabsch_rotation(...)` —
      the same call the manual `_save_coordinate_pairing` already makes
      (`MovementWizard.py:1266`). Invoked from the existing SfP block
      (`StandardExperiment.py:283-286`). No new fitting math was needed:
      `KabschRotation.update()` already re-solves the full least-squares fit over all
      accumulated points on every call.
- [x] Added the opt-in flag `exctrl_refine_calibration_with_sfp`
      (`StandardExperiment.py:114`, default `False`, alongside the existing
      `exctrl_auto_move_stages`/`exctrl_enable_sfp`), recorded into every measurement's
      metadata (`StandardExperiment.py:521-523`) so a dataset always says whether its
      calibration was moving. Exposed in the main window as a
      "Refine stage calibration from Search-for-Peak results" checkbox
      (`MainWindowView.py:229-237`, `MainWindowModel.py:86-88,165`). It auto-disables
      with an explanatory reason when it cannot apply: no connected stages
      (`MainWindowModel.py:225-227`), search-for-peak not initialized (`:247-249`), or
      Search-for-Peak simply not enabled (`:168-175`) — since refinement is meaningless
      without a search actually running.
- [x] Acceptance policy implemented in `PeakSearcher`, so a bad search cannot poison
      the fit. `search_for_peak()` now returns a top-level `'search successful'` bool
      plus a human-readable `'calibration rejection reasons'` list
      (`PeakSearcher.py:660-682`), aggregated from three per-dimension checks:
      `'peak found'` (`:523,610` — false when the power meter returned non-finite data,
      the fit wanted to move >1.5x the search radius, or the scan's dynamic range was
      under `NO_PEAK_FOUND_DYNAMIC_RANGE_DB`), `'verification passed'` (`:625-626`,
      built on the fresh-power verification added earlier), and the new
      `'near search radius edge'` (`:595-611`) which flags a fit whose optimum lands
      beyond `NEAR_EDGE_REJECT_FRACTION` (0.9, `:35`) of the search radius — the peak
      may be clipped by the scan window, so the stage still moves there but the
      position is not trusted as an absolute reference. `_refine_calibration_from_sfp`
      rejects and logs anything that fails these (`StandardExperiment.py:432-444`).
- [x] Timing semantics decided: **immediate**. Each accepted pairing re-solves the
      Kabsch fit right away, so the next `move_to_device` in the same sweep already
      benefits — mapping accuracy compounds as the sweep progresses, which is the
      whole point of the feature. The reproducibility cost (coarse-move targeting is
      not identical on a re-run) is accepted, and is mitigated by the acceptance
      policy above plus the per-measurement `"calibration refinement"` record
      (`StandardExperiment.py:284-286`) that captures exactly what was applied when.
- [x] Re-measurement behavior decided: **replace**. `KabschRotation.update()` gained a
      `replace_existing` flag (`Transformations.py:786-845`, default `False` so all
      existing callers keep raising on duplicates) backed by a new
      `remove_pairing_for_device()` (`:749-784`) which drops the stored pairing, prunes
      its coordinate-matrix columns, and re-solves — clearing the transformation
      outright if the removal drops below `MIN_POINTS`, rather than leaving a stale
      rotation behind an `is_valid == False` gate. Auto-refinement passes
      `replace_existing=True`, so re-measuring a known device moves its reference point
      to where the device actually is now, letting the fit follow real
      thermal/mechanical drift instead of staying anchored to a stale morning
      measurement.
- [x] Surfaced live: one `INFO` log line per stage each time a device feeds the
      calibration — "Calibration refined from device X: <stage> now has N pairings,
      fit residual Y um" (`StandardExperiment.py:486-492`) — using the residual added
      in the section below, so mapping accuracy can be watched improving during a run.
      The same information is persisted per-measurement under
      `data["calibration refinement"]` (per-stage pairing count, residual, and both
      coordinates), and rejected searches log a warning naming the failed check.
      5 new unit tests cover the replace/remove behavior
      (`Transformations_test.py:721-806`): replace-vs-raise on duplicate devices,
      removal of an unknown device, transformation clearing when dropping below
      `MIN_POINTS`, and that replacing a pairing actually pulls the fit toward the
      newly measured position.

### Calibration quality visibility (needed to make auto-refinement trustworthy)
- [x] Computed and exposed a real fit-residual/RMSD for the Kabsch fit —
      `KabschRotation.get_fit_residual_um()` (`Transformations.py:873-892`) computes
      the aggregate RMSD (um) between the fit's predicted stage positions and the
      actually-recorded stage positions across all pairings, returning `None` while
      not yet valid (mirroring `get_z_plane_angles()`'s existing convention,
      `:847-871`). Exposed via `Calibration.get_kabsch_rotation_residual_um()`
      (`Calibration.py:405-415`) and shown in the Calibration Wizard right next to
      the existing plane-angle display (`MovementWizard.py:1105-1109`).
- [x] Surfaced per-pairing residual via `KabschRotation.get_pairing_residuals_um()`
      (`Transformations.py:894-915`, returns `(pairing, residual_um)` per pairing in
      `self.pairings` order) and `Calibration.get_kabsch_rotation_pairing_residuals_um()`
      (`Calibration.py:417-427`). Wired into the "Defined Pairings" table as a new
      "Residual (um)" column (`MovementWizard.py:1018-1039`), so a single bad point
      stands out directly in the same table the existing "Remove selected pairings"
      button already operates on — no new removal mechanism needed, the existing one
      now has the residual to act on.
- [x] Added a "Run Calibration Health Check..." button (one per stage calibration,
      `MovementWizard.py:1111-1115`) using leave-one-out validation:
      `KabschRotation.get_leave_one_out_errors_um()` (`Transformations.py:917-959`)
      refits on all-but-one pairing and measures the prediction error at the held-out
      point, for every pairing (needs `MIN_POINTS + 1` = 4 total points; returns `[]`
      below that, same floor `test_transformation_estimates_fourth_variable` already
      exercises at `Transformations_test.py:603-624`). Exposed via
      `Calibration.get_kabsch_rotation_leave_one_out_errors_um()` (`Calibration.py:429-439`)
      and surfaced as a per-device ranked messagebox
      (`_run_calibration_health_check`, `MovementWizard.py:1244-1276`) highlighting the
      worst-predicted device.
      7 new unit tests added (`Transformations_test.py:808-874`): not-yet-valid case
      for all three methods, near-zero residual on exact synthetic rigid data,
      ordering/count against the real `vacherin.json` fixture, and the 4-point
      leave-one-out floor. Static-checked (`py_compile` + import-only sanity check,
      both clean) but not executed — run with:
      `pytest LabExT/Tests/Movement/Transformations_test.py -v`

### "3-point calibration" gaps worth knowing about
- [ ] No scale/affine correction exists anywhere in `Movement/` (confirmed: zero
      matches for affine/scale in that package) — only rotation + translation. A
      GDS-unit mismatch, thermal drift, or stage-calibration drift that introduces a
      scale error can't be corrected by any current transform tier. Worth a 4th tier
      (similarity transform: rotation + uniform scale + translation, gated behind 4+
      points to stay well-conditioned) if scale error is ever suspected in practice.
- [ ] `SinglePointOffset` never benefits from extra points the way Kabsch does
      (`update()` always just overwrites the one stored pairing,
      `Transformations.py:570-589`) — worth clarifying in the GUI hint text so a user
      collecting a 2nd point while still below Kabsch's 3-point floor doesn't assume
      it's already improving the fit.
- [ ] Both real-world chip importers only ever produce 2D device positions (z
      defaults to 0), so the Kabsch "3D" fit is always given coplanar chip-side
      points in practice — this structurally limits what `get_z_plane_angles()` can
      actually detect (a truly tilted chip vs. a flat design file with no Z data at
      all). Worth a docstring note wherever that method is defined/surfaced.

### Chip-mapping data quality (upstream of calibration; found while tracing the GDS path)
- [ ] `configs/gds_file_markup.ipynb` (the only GDS-derived import path in the repo)
      has two concrete inconsistencies worth fixing if it's actually used for real
      chip imports: its working cells reference different calibration labels ("7500"
      vs "8600"), and only one of them applies `np.flip` to swap X/Y — so which cell
      you happen to run silently changes the resulting coordinate convention. Pick one
      calibration-label and one axis-order convention and make them explicit
      parameters instead of ad-hoc per-cell choices.
- [ ] The same notebook never writes an `Outputs` key, so every device imported
      through it defaults to `out_position == [0.0, 0.0]` (via `IBMMaskDescription`'s
      missing-key fallback) — any output-role stage move for such a chip currently
      targets a meaningless default, not a real per-device location. Likely the
      single highest-value fix in this whole area if this notebook is the real
      chip-import path in use.
- [ ] Consider promoting this notebook's logic into a proper `ChipSourceStep` plugin
      (`LabExT/Wafer/ChipSourceAPI/`) alongside `PhoenixPhotonics`/`IBMMaskDescription`,
      so GDS import goes through the same reviewed/tested path as the other two
      formats instead of living as an ad-hoc notebook carrying the two bugs above.

### Feedback-loop integration boundaries
- [x] Kept `PeakSearcher`/`EdgeSearcher` stage-coordinate-only as designed — the
      auto-refinement lives entirely at the `StandardExperiment` caller level
      (`StandardExperiment.py:272-286,403-492`), which already has the `Device` and the
      mover/calibrations in scope right where `search_for_peak()` is called.
      `PeakSearcher.py` gained no chip-coordinate, `Calibration`, or `Transformation`
      awareness at all; it only reports *quality metadata* about its own search
      (`'search successful'` / `'calibration rejection reasons'`), leaving the caller
      to decide what to do with it. Verified: `PeakSearcher.py` still has zero
      references to `Calibration`/`Transformation`/`CoordinatePairing`.
- [ ] Decide whether the same auto-refinement should apply if/when `EdgeSearcher` is
      ever driven from a sweep the same way `PeakSearcher` is today — currently only
      `PeakSearcher` is wired into `StandardExperiment`. If so, `EdgeSearcher` would
      first need equivalent quality/acceptance metadata to gate on, since
      `_refine_calibration_from_sfp`'s acceptance policy is built on the fields
      `search_for_peak()` returns.

### Housekeeping (found incidentally; low priority, unrelated to the core ask)
- [ ] `MenuListener.client_edge_searcher` is defined twice, identically
      (`LabExT/View/MenuListener.py:262-270` and `:272-280`) — dead duplicate, the
      second silently shadows the first.
- [ ] `EdgeAlign.py` (`LabExT/Measurements/EdgeAlign.py`) is placeholder/dead code
      (demo buttons literally labeled "red"/"green"/"yellow"/"joel", ~90 lines of real
      logic commented out) with no chip/calibration awareness either — same file
      already flagged in `peak_searcher.md`'s GUI/integration section; noted again
      here since it surfaced independently in this research.
