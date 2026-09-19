# Kubernetes Debug Cluster Source Attribution

This directory vendors a bounded documentation snapshot from the Kubernetes website repository for the EvalGate EG-018 real-world showcase.

- Upstream repository: https://github.com/kubernetes/website
- Upstream commit: aa4e9e6dee49106155072a44ef997b91722243ec
- Approved path: content/en/docs/tasks/debug/debug-cluster/
- Vendored files: the 11 Markdown files listed in data/manifests/kubernetes-debug-cluster-v1.json
- License: Creative Commons Attribution 4.0 International (CC BY 4.0), copied in CC-BY-4.0.txt
- Transformation: files are stored as strict UTF-8, normalized to Unicode NFC, CRLF/CR converted to LF, Kubernetes site-root Markdown links converted to absolute https://kubernetes.io/docs/... URLs, with exactly one terminal LF. No content is fetched at runtime.
- Attribution: Kubernetes documentation is copyright The Kubernetes Authors and licensed under CC BY 4.0.
- Trademark/no endorsement: Kubernetes is a trademark of The Linux Foundation. EvalGate is not endorsed by or affiliated with Kubernetes, CNCF, or The Linux Foundation.

Questions and labels in the EG-018 showcase are EvalGate-authored demonstration data. They are not production-user traffic and do not form an external benchmark.