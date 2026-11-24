# Medicine groups audit, register of 2026-11-24

## Sources

- register_file: register.xml
- register_sha256: b364878dbcc8a375be5091f0e4e814e34f36d2cec6f839c7db5f064fa736d5a5
- register_bytes: 224813053
- shortage_file: 2026-11-24.txt
- shortage_sha256: 6ce6c5d9cf2c7dd4126e5beec5b96244872e81c4cbc0483625057678e4e67787
- shortage_bytes: 64857
- shortage_snapshot_date: 2026-11-24
- register_source_name: Perusrekisteri2026.xml
- register_date: 2026-11-24
- register_last_modified: Tue, 24 Nov 2026 00:30:58 GMT
- shortages_last_modified: Mon, 23 Nov 2026 23:20:01 GMT
- snapshot_date: 2026-11-24
- groups_json_sha256: 2082f01fe6b103e9f1b135ef8d0266d0e5deed4adbc685185cf2b81c9aa1f27d

18445 register packages with a VNR in 9453 groups. 756 VNRs in the current shortage file: 753 joined to one register package, 3 ambiguous (on two register records: 018486, 370212, 424765), 0 not found. 4 joined by an old VNR.

Register VNRs on two records: 54. On the market means: register flag Kaupan is 1 and the market entry and exit dates agree. Packages that the market dates put on the market while the flag is not 1: 8 (006334, 056292, 161756, 196986, 414779, 425281, 464436, 540878); they are not counted.

## all: 9453 groups

- unsure: 6227
  - authorisation_identity_missing: 1
  - biological_several_products: 190
  - composition_differs: 20
  - composition_not_verified: 119
  - device_not_verified: 703
  - no_marketing_authorisation_record: 8
  - parallel_not_linked: 932
  - presentation_not_verified: 1445
  - product_substances_inconsistent: 4
  - register_group_disagrees: 57
  - route_not_stated: 3076
  - several_products_no_register_group: 644
  - strength_not_stated: 937
  - veterinary: 940
  - vnr_listed_twice: 79
- first-release candidates (not unsure, one product record, one known container): 2343
- groups kept out of the first release only by the container guard: 39
- single-package groups: 6053
- groups with several active substances: 1622
- groups with a parallel import: 865; with a parallel distribution: 399
- groups flagged for quantity review: 20
- merges_different_substance: 0
- merges_different_strength: 0
- merges_different_form: 0
- merges_different_route: 0

## on market: 5299 groups

- unsure: 2484
  - biological_several_products: 176
  - composition_differs: 12
  - composition_not_verified: 76
  - device_not_verified: 485
  - no_marketing_authorisation_record: 5
  - parallel_not_linked: 322
  - presentation_not_verified: 982
  - register_group_disagrees: 55
  - route_not_stated: 4
  - several_products_no_register_group: 193
  - strength_not_stated: 369
  - veterinary: 734
  - vnr_listed_twice: 6
- first-release candidates (not unsure, one product record, one known container): 1945
- groups kept out of the first release only by the container guard: 35
- single-package groups: 3178
- groups with several active substances: 880
- groups with a parallel import: 301; with a parallel distribution: 342
- groups flagged for quantity review: 12
- merges_different_substance: 0
- merges_different_strength: 0
- merges_different_form: 0
- merges_different_route: 0

## in current shortage: 583 groups

- unsure: 220
  - biological_several_products: 16
  - composition_differs: 1
  - composition_not_verified: 14
  - device_not_verified: 34
  - parallel_not_linked: 58
  - presentation_not_verified: 83
  - register_group_disagrees: 12
  - several_products_no_register_group: 10
  - strength_not_stated: 24
  - veterinary: 37
  - vnr_listed_twice: 5
- first-release candidates (not unsure, one product record, one known container): 135
- groups kept out of the first release only by the container guard: 0
- single-package groups: 213
- groups with several active substances: 77
- groups with a parallel import: 54; with a parallel distribution: 64
- groups flagged for quantity review: 1
- merges_different_substance: 0
- merges_different_strength: 0
- merges_different_form: 0
- merges_different_route: 0

## Register substitution groups against these groups

```
{
 "register_groups": 1685,
 "register_groups_spanning_several_medicine_groups": 612,
 "differences_among_those": {
  "device": 60,
  "form": 146,
  "presentation": 153,
  "routes": 38,
  "strength_text": 56,
  "substances": 131
 }
}
```

## Current shortages of human medicines: other packages by register code against the same-key group

Internal comparison counts. They are not availability claims and say nothing about what can replace what.

```
{
 "register code: no_register_code; same-key group: none": 60,
 "register code: no_register_code; same-key group: other_package_listed": 9,
 "register code: no_register_code; same-key group: unsure_group": 48,
 "register code: none; same-key group: none": 47,
 "register code: none; same-key group: unsure_group": 14,
 "register code: other_package_listed; same-key group: none": 46,
 "register code: other_package_listed; same-key group: other_package_listed": 343,
 "register code: other_package_listed; same-key group: unsure_group": 147
}
```
