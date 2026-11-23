# Medicine groups audit, register of 2026-11-23

## Sources

- register_file: register.xml
- register_sha256: ab45fbfde836c419d0a95a6833ceb221be991e82d47e8104e9f6ca8e435dc7d1
- register_bytes: 224750458
- shortage_file: 2026-11-23.txt
- shortage_sha256: c5691bc5e48e42869591ba5bb3a19f32cff249bf90ea873b62e39a217b12bf80
- shortage_bytes: 64978
- shortage_snapshot_date: 2026-11-23
- register_source_name: Perusrekisteri2026.xml
- register_date: 2026-11-23
- register_last_modified: Mon, 23 Nov 2026 00:31:00 GMT
- shortages_last_modified: Sun, 22 Nov 2026 23:20:01 GMT
- snapshot_date: 2026-11-23
- groups_json_sha256: d4fe036e0fc9241878bc2db200f7b50e0ec21e15ba73ed54e1784d0b72a9a32d

18440 register packages with a VNR in 8585 groups. 757 VNRs in the current shortage file: 754 joined to one register package, 3 ambiguous (on two register records: 018486, 370212, 424765), 0 not found. 8 joined by an old VNR.

Register VNRs on two records: 54. On the market means: register flag Kaupan is 1 and the market entry and exit dates agree. Packages that the market dates put on the market while the flag is not 1: 10 (006334, 056292, 161756, 188377, 192949, 196986, 414779, 425281, 464436, 540878); they are not counted.

## all: 8585 groups

- unsure: 4801
  - authorisation_identity_missing: 1
  - biological_several_products: 178
  - composition_differs: 20
  - composition_not_verified: 122
  - device_not_verified: 151
  - no_marketing_authorisation_record: 8
  - parallel_not_linked: 925
  - product_substances_inconsistent: 4
  - register_group_disagrees: 59
  - route_not_stated: 2766
  - several_products_no_register_group: 643
  - strength_not_stated: 804
  - veterinary: 848
  - vnr_listed_twice: 79
- first-release candidates (not unsure, one product record): 2880
- single-package groups: 4932
- groups with several active substances: 1479
- groups with a parallel import: 861; with a parallel distribution: 391
- groups flagged for quantity review: 20
- merges_different_substance: 0
- merges_different_strength: 0
- merges_different_form: 0
- merges_different_route: 0

## on market: 4910 groups

- unsure: 1552
  - biological_several_products: 159
  - composition_differs: 12
  - composition_not_verified: 80
  - device_not_verified: 138
  - no_marketing_authorisation_record: 5
  - parallel_not_linked: 323
  - register_group_disagrees: 57
  - route_not_stated: 4
  - several_products_no_register_group: 184
  - strength_not_stated: 329
  - veterinary: 673
  - vnr_listed_twice: 6
- first-release candidates (not unsure, one product record): 2462
- single-package groups: 2660
- groups with several active substances: 831
- groups with a parallel import: 301; with a parallel distribution: 339
- groups flagged for quantity review: 12
- merges_different_substance: 0
- merges_different_strength: 0
- merges_different_form: 0
- merges_different_route: 0

## in current shortage: 562 groups

- unsure: 150
  - biological_several_products: 15
  - composition_differs: 1
  - composition_not_verified: 14
  - device_not_verified: 18
  - parallel_not_linked: 53
  - register_group_disagrees: 13
  - several_products_no_register_group: 12
  - strength_not_stated: 22
  - veterinary: 34
  - vnr_listed_twice: 4
- first-release candidates (not unsure, one product record): 167
- single-package groups: 161
- groups with several active substances: 74
- groups with a parallel import: 49; with a parallel distribution: 62
- groups flagged for quantity review: 1
- merges_different_substance: 0
- merges_different_strength: 0
- merges_different_form: 0
- merges_different_route: 0

## Register substitution groups against these groups

```
{
 "register_groups": 1685,
 "register_groups_spanning_several_medicine_groups": 541,
 "differences_among_those": {
  "device": 60,
  "form": 146,
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
 "register code: no_register_code; same-key group: none": 77,
 "register code: no_register_code; same-key group: other_package_listed": 20,
 "register code: no_register_code; same-key group: unsure_group": 23,
 "register code: none; same-key group: none": 53,
 "register code: none; same-key group: unsure_group": 8,
 "register code: other_package_listed; same-key group: none": 52,
 "register code: other_package_listed; same-key group: other_package_listed": 376,
 "register code: other_package_listed; same-key group: unsure_group": 106
}
```
