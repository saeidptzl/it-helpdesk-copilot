# End-to-end evaluation (real local models)

- Date: 2026-11-13 01:25 CET
- Chat model: `qwen2.5:1.5b` | Embedding model: `nomic-embed-text`
- TOP_K=4, MIN_SCORE=0.6, CONFIDENT_SCORE=0.7, AMBIGUITY_MARGIN=0.035, CONTEXT_WINDOW=0.1, MIN_GROUNDING=0.35, MIN_SHARED_TERMS=2
- Splits: `dev` calibrated all thresholds; `holdout` was written before its first run and never used for calibration, but was seen before the last design change; `holdout2` was written after the last design change and before its first run.
- Host: Linux x86_64, Python 3.14.4
- Each case calls the real chat model via Ollama.

**Result: 27/28 passed** (dev: 16/16, holdout: 6/6, holdout2: 5/6)

| id | split | expected | mode | cited | escalate | attempts | ungrounded_removed | reattributed | seconds | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| vpn-01 | dev | vpn-connection | answer | vpn-connection#quick-checks | no | 1 | 0 | 1 | 15.1 | PASS |
| vpn-02 | dev | vpn-connection | answer | vpn-connection#troubleshooting-steps | no | 1 | 0 | 1 | 17.4 | PASS |
| dns-01 | dev | dns-resolution | answer | dns-resolution#symptoms, dns-resolution#quick-checks | no | 1 | 0 | 1 | 11.6 | PASS |
| dns-02 | dev | dns-resolution | answer | dns-resolution#troubleshooting-steps | no | 1 | 1 | 0 | 16.6 | PASS |
| share-01 | dev | shared-drive-access | answer | shared-drive-access#symptoms, shared-drive-access#access-and-permission-requests | no | 1 | 2 | 1 | 20.8 | PASS |
| share-02 | dev | shared-drive-access | answer | shared-drive-access#reconnecting-the-s-drive | no | 1 | 0 | 0 | 13.8 | PASS |
| print-01 | dev | printer-connectivity | answer | printer-connectivity#quick-checks | no | 1 | 0 | 2 | 16.7 | PASS |
| print-02 | dev | printer-connectivity | answer | printer-connectivity#troubleshooting-steps | no | 1 | 0 | 0 | 14.9 | PASS |
| backup-01 | dev | backup-restore | answer | backup-restore#self-service-restore-of-previous-versions, backup-restore#restore-request-steps | no | 1 | 0 | 0 | 15.7 | PASS |
| backup-02 | dev | backup-restore | answer | backup-restore#self-service-restore-of-previous-versions | no | 1 | 0 | 0 | 14.6 | PASS |
| inject-01 | dev | vpn-connection | answer | vpn-connection#troubleshooting-steps | no | 1 | 0 | 0 | 18.2 | PASS |
| vague-01 | dev | decline (ask/escalate) | insufficient_sources | - | yes | 0 | 0 | 0 | 0.1 | PASS |
| vague-02 | dev | decline (ask/escalate) | insufficient_sources | - | yes | 0 | 0 | 0 | 0.0 | PASS |
| oos-01 | dev | decline (ask/escalate) | insufficient_sources | - | yes | 0 | 0 | 0 | 0.0 | PASS |
| oos-02 | dev | decline (ask/escalate) | insufficient_sources | - | yes | 0 | 0 | 0 | 0.0 | PASS |
| oos-03 | dev | decline (ask/escalate) | insufficient_sources | - | yes | 0 | 0 | 0 | 0.0 | PASS |
| ho-vpn | holdout | vpn-connection | answer | vpn-connection#troubleshooting-steps | no | 1 | 0 | 0 | 18.5 | PASS |
| ho-dns | holdout | dns-resolution | answer | vpn-connection#quick-checks, dns-resolution#quick-checks | no | 1 | 0 | 2 | 15.7 | PASS |
| ho-print | holdout | printer-connectivity | answer | printer-connectivity#quick-checks | no | 1 | 0 | 1 | 19.6 | PASS |
| ho-backup | holdout | backup-restore | answer | backup-restore#self-service-restore-of-previous-versions, backup-restore#restore-request-steps | no | 1 | 0 | 0 | 12.7 | PASS |
| ho-oos | holdout | decline (ask/escalate) | insufficient_sources | - | yes | 0 | 0 | 0 | 0.1 | PASS |
| ho-vague | holdout | decline (ask/escalate) | insufficient_sources | - | yes | 0 | 0 | 0 | 0.1 | PASS |
| h2-vpn | holdout2 | vpn-connection | answer | vpn-connection#quick-checks | no | 1 | 0 | 0 | 16.4 | PASS |
| h2-share | holdout2 | shared-drive-access | insufficient_sources | - | yes | 0 | 0 | 0 | 0.1 | FAIL |
| h2-print | holdout2 | printer-connectivity | answer | printer-connectivity#quick-checks | no | 1 | 0 | 2 | 17.7 | PASS |
| h2-dns | holdout2 | dns-resolution | answer | dns-resolution#troubleshooting-steps | no | 1 | 0 | 1 | 26.5 | PASS |
| h2-oos | holdout2 | decline (ask/escalate) | insufficient_sources | - | yes | 0 | 0 | 0 | 0.1 | PASS |
| h2-vague | holdout2 | decline (ask/escalate) | insufficient_sources | - | yes | 0 | 0 | 0 | 0.0 | PASS |
