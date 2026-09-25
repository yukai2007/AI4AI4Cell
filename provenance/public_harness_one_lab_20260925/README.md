# Public-harness one-laboratory rerun

This rerun corrects the access contract used for the task-adapted
AI-Scientist-v2 and AI-Researcher comparison.  These public controllers do not
implement BioCoLoop's collaborative training/evaluation mechanism, so they
receive laboratory 0 only.  BioCoLoop retains the ten-laboratory result from
the prespecified core experiment.

The controlled quantities are unchanged: seed 42, local
Qwen2.5-7B-Instruct, twelve executable designs, at most six proposals, 100
training rounds per valid candidate, task-specific development selection and
the frozen held-out scorers.  The queue started all eight available GPUs with
independent jobs; the two long DTI trajectories remain sequential within each
controller because every proposal depends on the preceding measured evidence.

`runtime_source/` contains the lab-0 shim, controller launcher, GPU supervisor,
held-out evaluator, DTI recovery entry point and read-only independent verifier
used for the run. The generated table snapshot records the run manifest,
supervisor ledger, result receipts, selected checkpoint hashes and source
hashes. A score is published only after the stored predictions pass an
independent metric recomputation.

The original AI-Researcher DTI scoring launch used an interpreter that lacked
the registered TAPB environment. It stopped after writing the evaluation seal
and before accessing a test response. `resume_sealed_dti.py` checks the sealed
development selection, source hashes and unchanged held-out seal, then invokes
the original scorer with the interpreter named by the task manifest. The
resulting 86.01 AUROC passes the same read-only verifier as the other scored
cells. AI-Scientist-v2's DTI tree search instead fails before selection sealing
after three fully trained candidates, so the publication reports
`F_pipe` rather than scoring an incomplete controller run.

The machine-local evidence root is
`/liziqing/yukai/AI4AI4Cell/results/public_harness_20260925/one_lab_v1`.
Large checkpoints and predictions are not copied into the paper repository.
