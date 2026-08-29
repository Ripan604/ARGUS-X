# Preliminary adjacent-art notes

This is a fast engineering search, not a freedom-to-operate opinion, validity analysis, claim chart, or substitute for a patent attorney and professional patent search.

## Material adjacent references

| Reference | What it appears to cover | ARGUS engineering distinction to investigate |
|---|---|---|
| [EP2214009A2](https://patents.google.com/patent/EP2214009A2/en) | Bayesian inversion of wave disturbance for defect localization | ARGUS closes the loop by choosing the next source/receiver/excitation from the live posterior |
| [US6981417B1](https://patents.google.com/patent/US6981417B1/en) | Adaptive scanning acoustic microscopy using processed perturbation information to revise scanning | ARGUS ranks discrete counterfactual physical experiments using hypothesis-response separation, cost, and repetition |
| [US9964468B1](https://patents.google.com/patent/US9964468B1/en) | Optimizing sensor placement for structural health monitoring from scenarios/models | ARGUS is sequential, measurement-conditioned, and jointly chooses actuator/receiver/spectral parameters rather than a fixed network |
| [US12548141B2 / US20230401694A1](https://patents.google.com/patent/US20230401694A1/en) | Active-learning selection of semiconductor inspection locations and incremental model training | ARGUS selects a physical wave experiment to discriminate latent internal states, not locations for image labeling |
| [Flynn & Todd, 2010](https://doi.org/10.1117/12.847744) | Bayesian experimental design for ultrasonic guided-wave sensor placement | Important non-patent prior art; investigate whether sequential movable experiments and the specific counterfactual/cost loop add a non-obvious implementation |
| [Capellari et al., 2018](https://doi.org/10.1061/AJRUA6.0000966) | Structural-health sensor networks selected by Shannon information gain | Fixed sensor-network design is adjacent to ARGUS’s information objective |
| [Bayesian Lamb-wave minimal sensing, 2022](https://doi.org/10.1016/j.ndteint.2022.102626) | Bayesian damage assessment using learned surrogate models and limited sensors | Adjacent inference/surrogate work; ARGUS’s planner loop needs careful claim differentiation |

## Search conclusion

The broad ingredients—Bayesian wave localization, optimized sensor placement, adaptive acoustic scanning, and active-learning inspection—already exist. Any defensible filing likely needs to focus on a specific implemented combination and control loop, not “AI + acoustics + uncertainty” in the abstract. The strongest current candidate is the posterior-conditioned, multi-parameter physical experiment selection mechanism that uses counterfactual predicted response disagreement, explicit execution cost/redundancy, recursive evidence fusion, and traceable human placement guidance.

Search the claims and patent families above, their citations, continuations, and non-English family members before drafting. Also search CPC classes covering ultrasonic/acoustic material investigation, structural health monitoring, adaptive experiment design, and active learning.
