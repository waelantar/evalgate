# Evaluation governance

Evaluation is not implemented by the foundation. The governing design is `BLUEPRINT.md` section 10 and ADR-0006.

EG-009 owns the golden set and metric library. EG-010 owns the reviewed retrieval baseline and PR policy. EG-015 owns protected live-generation evidence. CI artifacts never write to deployed application state, and no baseline is updated automatically.
