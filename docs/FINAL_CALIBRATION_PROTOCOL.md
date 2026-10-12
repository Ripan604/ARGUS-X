# Final task-conditioned reference-design validation protocol

Recorded before the numerical run. This is a synthetic scalar direct-arrival
calibration study, not defect-localization or physical apparatus validation.

- Sixty-four final paired seeds 83000-83063; three references per policy.
- Policies: cyclic first-feasible (existing engine reference order), task-conditioned,
  and repeated-short reference as a separate identifiability failure control.
- Reference paths 0.18, 0.36, 0.54 m on a 600 x 400 mm panel; same bank and budgets.
- A uniform 20 x 20 posterior and fixed diagnostic geometry define the full-grid
  propagation-arrival design target. No hidden truth enters selection.
- Hidden speed/timing are seeded draws from the declared prior within its bounds.
  Scalar observations use t0+d/v plus shared per-step Gaussian innovations.
- Acquisition noise is computed once per case from the sealed true speed and
  declared timing/pose noise, independent of each policy's inference state.
  The reference updater uses its current assumed noise contract. All policies
  receive the same per-step Gaussian noise innovation and acquisition variance.
- Report all runs, selected paths, before/after modeled variance, held-out target
  arrival error, velocity/timing errors and paired bootstrap intervals.
- Primary outcome: held-out target arrival RMSE across grid cells in microseconds.
  This is propagation prediction, not defect position or safety probability.
- Do not tune to the results, remove seeds, infer field accuracy, or present
  covariance conditioning or Bayesian design as newly invented mathematics.
- Hash every backend/app Python source and the validation script before/after.

An earlier 81000-series development pilot used a repeated-short baseline. It is
retained as final_task_calibration_pilot_repeated_path.json and must not be
represented as the existing engine's rotating first-feasible policy. The corrected
comparison uses fresh seeds and reports the cyclic baseline as its primary pair.

The 82000-series development run had estimator-dependent acquisition noise. It
is retained as final_task_calibration_pilot_coupled_noise.json and excluded from
final claims. The corrected final fixture uses independent acquisition physics
and fresh 83000-series seeds; this correction is not policy hyperparameter tuning.
