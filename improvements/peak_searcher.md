# Peak Searcher — Improvement To-Do List

Findings from a code review of `LabExT/SearchForPeak/PeakSearcher.py` and its
surrounding stage/power-meter/GUI infrastructure (fiber-array-to-PIC alignment).

## Bugs (fix first)

- [x] ~~Fix broken `swept SfP` mode~~ — **removed entirely** instead of fixed (it was
      broken, gated to hardware nothing in production uses, and not worth maintaining).
      `PeakSearcher` now only implements stepped SfP; the `SfP type` selector and all
      swept-only parameters are gone. See "Proposed alternative search algorithms"
      below for ideas on a future replacement/faster mode.
- [x] Finish/clean up the in-progress low-signal-contrast rejection check — replaced
      the placeholder `'(sike (lol))'` message with a real, distinct warning (now
      logged via `self.logger.warning`, which it previously wasn't) and pulled the
      hardcoded `3` out into a module-level `NO_PEAK_FOUND_DYNAMIC_RANGE_DB` constant.
      (`PeakSearcher.py:549-556`)
- [x] Fix `ThorlabsKCube.move()`'s backlash compensation — replaced the hand-rolled
      jog+backlash simulation entirely with the Kinesis controller's own native
      `move_by`/`move_to` commands and its native hardware backlash-compensation
      setting (`setup_gen_move`, confirmed supported on the KDC101/Z825 hardware this
      driver targets), configured once per channel instead of recomputed every move.
      This also fixes a more serious bug found while researching the fix: the old code
      always called `jog(direction="+")` regardless of the sign of the requested move
      (per Thorlabs' own jog-parameter docs, step size is an unsigned magnitude and
      direction is always independently specified — never derived from step size's
      sign), so negative-direction moves may have silently jogged the wrong way.
      `move_by`/`move_to` take signed distances/positions directly, so this class of
      bug is gone. Each axis's `move()` is now also a no-op when the requested
      displacement is negligible, so backlash is only ever compensated by the firmware
      for the axis that actually moves. (`LabExT/Movement/Stages/ThorlabsKCube.py`)
- [x] `EdgeSearcher.py`'s `estimated_through_power` is now updated after every
      `capture_data()` call (tracks the running max of all measured powers so far).
      Fixed the identically-broken `current_coordinates` in the same pass — it was
      only ever set to the *pre-move* position, never updated after the stage actually
      moved, so `close_instruments()`'s final log/results reflected the wrong position.
      (`LabExT/SearchForPeak/EdgeSearcher.py`)
- [x] Updated `PeakSearcher`'s class docstring to document the Switch/`M=1-4`, 4-PD
      merit function, and 3-pass parameters. (`PeakSearcher.py:39-106` vs. `:267-291`)
- [x] Resolved the "should NOT be used in an experiment routine" contradiction — the
      docstring now explains the real constraint accurately: `PeakSearcher` doesn't
      implement the standard `Measurement.algorithm()` interface (so it can't be added
      as a regular sweep-able measurement in the wizard), but is used directly via
      `search_for_peak()`, including automatically by `StandardExperiment` as a
      pre-measurement alignment step. (`PeakSearcher.py:43-46`)
- [x] Added safety checks before moving stages in `EdgeSearcher.capture_data()`: reject
      non-finite (NaN/inf) increments outright, and reject any single-axis increment
      exceeding a new configurable `Max motor increment` parameter (default 50um).
      (`LabExT/SearchForPeak/EdgeSearcher.py`)

## Algorithm robustness

- [x] Verify the result: after the final move on each axis, a fresh averaged power
      reading (`_read_averaged_power`) is now taken and compared to
      `results['start through power']`, logging a warning if the axis ended up worse
      than the pass's starting power. Stored per-axis as `'verified through power'` in
      `results['fitting information']`, alongside a `'verification passed'` bool that
      the calibration auto-refinement in `StandardExperiment` uses as an acceptance
      gate (see `improvements/chip_mapping.md`). (`PeakSearcher.py:621-640`)
- [ ] Turn the single-shot "sample once, fit once, jump once" per axis into an
      iterative refinement: re-scan a smaller window around the new position and
      repeat until the fit stabilizes or a max-iteration count is hit, instead of
      relying entirely on the user manually configuring 3 passes with shrinking radii
      by hand. (`PeakSearcher.py:437-640`, pass loop at `:403-684`)
- [ ] Add a global timeout/watchdog for the whole search — today the worst case is
      unbounded (radius/stepsize × pause_time × axes × enabled passes, with no cap).
- [ ] Handle multi-modal responses (interference fringes, mode-hopping, multiple
      coupling lobes): a single 1D Gaussian fit over one scan window will silently
      lock onto whichever lobe dominates, with no multi-start fit or wider re-scan
      fallback if the window contains more than one peak.
- [x] ~~Made the outlier-rejection band in `fit_gaussian` configurable~~ — made
      configurable, then immediately **removed entirely** on the same day: the
      `Only High Power Points` checkbox and its (just-added) `Range` companion
      parameter were confirmed unused in practice (both were already unchecked for
      all 3 passes in the real running setup) and removed per-pass, along with the
      filtering code in `fit_gaussian` itself (`power_check_flag`/`power_range_db`
      are gone; `fit_gaussian(self, x_data, y_data)` now always fits on all points).
      Net effect matches how the setup was actually being run already.
- [ ] Consider replacing strict sequential per-axis independence (Left-X, Left-Y,
      Right-X, Right-Y, one shot each) with either repeated alternating passes over
      the same axes, or a genuine 2D optimizer, for cases where axes are coupled and
      a single pass per axis won't converge. `LabExT/Movement/PathPlanning.py`'s
      `PotentialField` class (`:303`, `_find_lowest_potential` at `:469`) already
      implements a gradient/potential-descent pattern in this codebase (for collision
      avoidance) that could serve as a template.

## Multi-stage / multi-PD design

- [ ] Reconsider the "max across all 4 PDs" merit function (`PeakSearcher.py:432,
      493`) — it picks whichever detector is currently strongest as a single scalar,
      rather than supporting "jointly maximize multiple outputs" or independent
      per-output searches. Make the merit function (max / sum / weighted) configurable
      per use case.
- [x] Refactored the copy-pasted "First/Second/Third Peak Search" parameter blocks —
      `get_default_parameter()` now builds all per-pass keys via a loop over the new
      `PASS_NAMES = ['First', 'Second', 'Third']` class attribute
      (`PeakSearcher.py:278-285`), and the per-pass reading logic in
      `search_for_peak()` collapsed from three `if/elif` branches down to a single
      f-string-driven block (`PeakSearcher.py:407-411`). Adding a 4th pass now means
      adding one name to `PASS_NAMES` — no other duplication. Flat parameter key names
      and their order are unchanged, so existing settings files stay compatible.

## Instrument/hardware layer

- [x] ~~Bridge the gap between the algorithm and deployed hardware (swept SfP gated to
      N7744A, real configs use `PowerMeterKoheronPD10R`)~~ — **moot**, swept SfP was
      removed entirely rather than extended. See "Proposed alternative search
      algorithms" below: any future fast/continuous-motion mode needs to support
      `PowerMeterKoheronPD10R` from the start, not repeat this mismatch.
- [ ] Harden `ThorlabsKCube` generally — it's the stage driver actually used in every
      real config, but is newer/less mature than the SmarAct driver (recent commit
      history shows active bug-fixing). Also fix the `acceleration` setter's signature
      mismatch (accepts an unused `max_velocity=None` kwarg inconsistent with how
      Python property setters are invoked elsewhere).
- [ ] Reconsider `MoverNew`'s global-only `speed_xy`/`acceleration_xy` (applies to
      every connected stage simultaneously) if any setup needs per-stage or per-axis
      speed tuning during a search. (`LabExT/Movement/MoverNew.py:464,524`)

## Performance

- [x] Reduce per-point latency in stepped SfP: `_read_averaged_power` now triggers
      all 4 power meters first, then fetches all 4, instead of 4 sequential blocking
      `.power` calls (`PeakSearcher.py:238-264`). Verified against the actual driver
      semantics before implementing: on the Keysight power meters, `trigger()` is a
      fire-and-forget `INIT:IMM` write and `fetch_power()` reads back the
      already-triggered value via `FETCH:POW?`, so triggering all 4 back-to-back lets
      their averaging windows overlap instead of stacking sequentially - that's where
      the real speedup happens. On `PowerMeterKoheronPD10R` (the class actually used
      in every real config), `trigger()` is a no-op and `fetch_power()` reads the same
      instantaneous DAQ value as `.power`, so this is behaviorally identical to before
      on that hardware - no regression, just no speedup there since there's no
      acquisition delay to hide in the first place.
- [ ] Make the fiber-settling delay (`pause_time_ms`, default 200 ms) adaptive —
      e.g. only wait longer if consecutive readings are still visibly changing —
      instead of a fixed sleep on every single point regardless of actual settling
      behavior.

## Code quality / testability

- [ ] Add unit tests for the pure, stateless Gaussian-fitting math (`_gaussian`,
      `_gaussian_param_initial_guess`, `fit_gaussian`) — zero test coverage today
      (`LabExT/Tests` has no `SearchForPeak` subdirectory at all) despite this being
      the crux of every accept/reject decision in the search.
- [ ] Break up the now ~390-line monolithic `search_for_peak()` method
      (`PeakSearcher.py:297-684`) into smaller, independently testable pieces
      (scan-one-axis, fit-and-decide, move-to-target) — currently instrument I/O,
      motion control, plotting, curve fitting, and decision logic are all interleaved
      in one method. `test_backlash()` (`:719-797`) and `_get_current_coordinates()`
      (`:709-717`) show the shape this decomposition could take. This grew slightly
      with the acceptance-signal tracking added for calibration auto-refinement, so
      the case for splitting it is a little stronger than before.
- [ ] Add schema validation to `update_params_from_savefile` — it currently writes
      every key from a save file into `self.parameters` with no check that the key
      still exists, so loading an old settings JSON against current code, or vice
      versa, will raise `KeyError` instead of failing gracefully. No longer an
      immediate risk (the current `PeakSearcher_settings.json` was already re-saved
      through the GUI and matches the current schema), but still worth hardening
      before the next parameter rename/removal recreates the risk.
      (`PeakSearcher.py:799-809`)
- [ ] Clean up the redundant `instr_switch` fetch — `self.get_instrument('Switch')` is
      called unconditionally, then called again inside the `if Switch Flag` block,
      with the first result silently discarded. (`PeakSearcher.py:323,348`)
- [ ] Name the remaining magic numbers as module-level constants with a comment on
      each: `1.5` (overshoot-rejection multiplier), `ftol=1e-8, maxfev=10000` (fit
      tolerance), the 10-color plotting-palette cap.

## GUI / integration

- [ ] Connect PeakSearcher to `LiveViewer` (`LabExT/View/LiveViewer/`) instead of
      keeping them entirely separate — today an operator has to switch between the
      generic LiveViewer (for live power monitoring via `PowerMeterCard`) and the
      separate modal Search-for-Peak window, with no shared plotting/position card.
- [ ] De-duplicate `LabExT/View/EdgeSearcherWindow.py` and
      `LabExT/View/SearchForPeakPlotsWindow.py` — near line-for-line copies of each
      other's window/model/controller structure — into a shared base class.
- [ ] Decide the fate of `LabExT/Measurements/EdgeAlign.py` — an abandoned prototype
      GUI (hardcoded placeholder buttons/position text, all real alignment logic
      commented out). Either finish it or remove it as dead code; as-is it's
      confusing prior art with a name that collides with `SearchForPeak/EdgeSearcher.py`.
- [ ] Expose a cancel/abort control in the GUI for long-running multi-pass searches,
      given there's currently no timeout and no way to stop a search partway through.

## Proposed alternative search algorithms (future work)

Ideas for a smarter/more efficient replacement or additional search mode, now that
swept SfP is gone. Proposals only — none of these are implemented yet.

- [ ] **Coarse-to-fine adaptive grid search**: evaluate a sparse coarse grid over the
      full radius first, then recursively zoom into the best cell at finer resolution.
      More robust to multi-modal/fringed responses than a single Gaussian fit over one
      window, and gives the iterative refinement the current single-shot-per-axis
      approach lacks (see the "Algorithm robustness" item above).
- [ ] **Joint 2D optimization** (e.g. `scipy.optimize.minimize` with Nelder-Mead/Powell,
      or reusing `LabExT/Movement/PathPlanning.py`'s existing `PotentialField`
      gradient-descent pattern) instead of independent per-axis 1D fits — better
      handles axes that are coupled (moving X changes the optimal Y).
- [ ] **Bayesian optimization / Gaussian-process surrogate search** (e.g.
      `scikit-optimize`): sample-efficient for an expensive-to-evaluate merit function
      (each point already costs a real stage move + settle time + multi-channel power
      read), and naturally models measurement noise instead of needing the current
      ad-hoc dynamic-range/overshoot rejection heuristics.
- [ ] **Cross-correlation/template matching** against a stored expected
      coupling-profile shape, as a fast coarse pre-alignment step before a fine
      per-axis refinement.
- [ ] If a fast continuous-motion ("swept"-style) mode is wanted again later, it needs
      to support the DAQ-based `PowerMeterKoheronPD10R` path actually used in every
      real config — not just the Keysight N7744A path the old implementation was
      hard-gated to — otherwise it will hit the same algorithm/hardware mismatch this
      removal fixed.
