# Retrieval evaluation (real embeddings, no LLM)

- Date: 2026-11-13 01:20 CET
- Chat model: `qwen2.5:1.5b` | Embedding model: `nomic-embed-text`
- TOP_K=4, MIN_SCORE=0.6, CONFIDENT_SCORE=0.7, AMBIGUITY_MARGIN=0.035, CONTEXT_WINDOW=0.1, MIN_GROUNDING=0.35, MIN_SHARED_TERMS=2
- Splits: `dev` calibrated all thresholds; `holdout` was written before its first run and never used for calibration, but was seen before the last design change; `holdout2` was written after the last design change and before its first run.
- Host: Linux x86_64, Python 3.14.4
- Generation is not called in this mode.

**Result: 26/28 passed** (dev: 16/16, holdout: 5/6, holdout2: 5/6)

| id | split | expected | top_section | top_score | guide_margin | shared_terms | gate | expected_guide_in_context | pass |
|---|---|---|---|---|---|---|---|---|---|
| vpn-01 | dev | vpn-connection | vpn-connection#quick-checks | 0.800 | 0.108 | 7 | ok | yes | PASS |
| vpn-02 | dev | vpn-connection | vpn-connection#symptoms | 0.823 | 0.117 | 5 | ok | yes | PASS |
| dns-01 | dev | dns-resolution | dns-resolution#symptoms | 0.797 | 0.134 | 9 | ok | yes | PASS |
| dns-02 | dev | dns-resolution | dns-resolution#symptoms | 0.826 | 0.143 | 8 | ok | yes | PASS |
| share-01 | dev | shared-drive-access | shared-drive-access#symptoms | 0.768 | 0.158 | 6 | ok | yes | PASS |
| share-02 | dev | shared-drive-access | shared-drive-access#symptoms | 0.693 | 0.067 | 4 | ok | yes | PASS |
| print-01 | dev | printer-connectivity | printer-connectivity#quick-checks | 0.720 | 0.098 | 6 | ok | yes | PASS |
| print-02 | dev | printer-connectivity | printer-connectivity#symptoms | 0.736 | 0.141 | 4 | ok | yes | PASS |
| backup-01 | dev | backup-restore | backup-restore#information-to-collect-for-a-restore-request | 0.699 | 0.063 | 7 | ok | yes | PASS |
| backup-02 | dev | backup-restore | backup-restore#self-service-restore-of-previous-versions | 0.676 | 0.036 | 4 | ok | yes | PASS |
| inject-01 | dev | vpn-connection | vpn-connection#symptoms | 0.808 | 0.087 | 8 | ok | yes | PASS |
| vague-01 | dev | gate blocks | backup-restore#restore-request-steps | 0.659 | 0.008 | 0 | no_clear_match | n/a | PASS |
| vague-02 | dev | gate blocks | shared-drive-access#symptoms | 0.631 | 0.035 | 0 | low_evidence | n/a | PASS |
| oos-01 | dev | gate blocks | backup-restore#restore-request-steps | 0.605 | 0.011 | 1 | no_clear_match | n/a | PASS |
| oos-02 | dev | gate blocks | printer-connectivity#escalation-criteria | 0.510 | 0.002 | 0 | low_score | n/a | PASS |
| oos-03 | dev | gate blocks | backup-restore#escalation-criteria | 0.589 | 0.005 | 1 | low_score | n/a | PASS |
| ho-vpn | holdout | vpn-connection | vpn-connection#symptoms | 0.747 | 0.103 | 10 | ok | yes | PASS |
| ho-dns | holdout | dns-resolution | vpn-connection#quick-checks | 0.744 | 0.002 | 8 | ok | yes | FAIL |
| ho-print | holdout | printer-connectivity | printer-connectivity#quick-checks | 0.674 | 0.062 | 6 | ok | yes | PASS |
| ho-backup | holdout | backup-restore | backup-restore#self-service-restore-of-previous-versions | 0.666 | 0.093 | 4 | ok | yes | PASS |
| ho-oos | holdout | gate blocks | backup-restore#what-is-backed-up | 0.595 | 0.017 | 1 | low_score | n/a | PASS |
| ho-vague | holdout | gate blocks | vpn-connection#information-to-collect | 0.631 | 0.007 | 0 | no_clear_match | n/a | PASS |
| h2-vpn | holdout2 | vpn-connection | vpn-connection#quick-checks | 0.790 | 0.115 | 4 | ok | yes | PASS |
| h2-share | holdout2 | shared-drive-access | shared-drive-access#symptoms | 0.679 | 0.024 | 4 | no_clear_match | no | FAIL |
| h2-print | holdout2 | printer-connectivity | printer-connectivity#information-to-collect | 0.697 | 0.070 | 2 | ok | yes | PASS |
| h2-dns | holdout2 | dns-resolution | dns-resolution#troubleshooting-steps | 0.713 | 0.066 | 7 | ok | yes | PASS |
| h2-oos | holdout2 | gate blocks | backup-restore#escalation-criteria | 0.592 | 0.002 | 2 | low_score | n/a | PASS |
| h2-vague | holdout2 | gate blocks | backup-restore#what-is-backed-up | 0.607 | 0.003 | 1 | no_clear_match | n/a | PASS |
