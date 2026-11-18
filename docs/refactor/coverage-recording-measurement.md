# Coverage recording measurement

Synthetic temporary data only; 2026-11-18. Threshold: adopt when repeated snapshot bytes reach 25% of total journal bytes in a 100-decision case with 20 or 500 notes. Repeated bytes are all snapshot copies after the first; exact compact serialization was checked against actual event bytes. Timing is informational.

Gate passed: 79.05% with 20 notes; 97.98% with 500 notes. Batching adopted; old records are read without rewriting.

| Concepts | Notes | Before bytes/events/reads | After bytes/events/reads | Before/after write seconds |
|---|---|---|---|---|
| 1 | 0 | 912/1/2 | 1098/1/2 | 0.0021/0.0022 |
| 1 | 20 | 2792/1/2 | 2978/1/2 | 0.0015/0.0017 |
| 1 | 500 | 49193/1/2 | 49379/1/2 | 0.0036/0.0057 |
| 10 | 0 | 6368/10/11 | 3042/1/2 | 0.0082/0.0018 |
| 10 | 20 | 25168/10/11 | 4922/1/2 | 0.0104/0.0021 |
| 10 | 500 | 489178/10/11 | 51323/1/2 | 0.0648/0.0120 |
| 100 | 0 | 61090/100/101 | 22572/1/2 | 0.2141/0.0066 |
| 100 | 20 | 249090/100/101 | 24452/1/2 | 0.3838/0.0120 |
| 100 | 500 | 4889190/100/101 | 70853/1/2 | 5.1293/0.0699 |

Every after case has one shared snapshot and one decision event. Reconstructed decisions were asserted identical. Full case sizes, byte fractions, search timings/read counts, platform, Python and source revision are in ignored `.artifacts/premacos/coverage-{before,after}.json`. These measurements establish synthetic duplication, not real workload frequency.
