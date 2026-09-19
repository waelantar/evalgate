# Kubernetes debug showcase dataset

`kubernetes-debug-v1` is an EvalGate-authored, human-reviewed demonstration dataset for EG-018. It is derived from the pinned Kubernetes website `content/en/docs/tasks/debug/debug-cluster/` source snapshot recorded in `data/manifests/kubernetes-debug-cluster-v1.json`.

The questions and labels are curated showcase cases. They are not production-user traffic, not an external benchmark, and not a claim that any model is generally better. Evidence IDs are deterministic for the reviewed corpus, `kubernetes-debug-heading-v1` chunking policy, and the reference embedding identity declared in `contracts/manifests/reference-embedding.json`.

Case mix: 12 development answerable cases, 3 calibration unanswerable cases, and 3 regression cases covering cross-document retrieval, terminology, and outdated-assumption behavior.