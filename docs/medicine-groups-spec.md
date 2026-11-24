# Medicine groups: what makes two packages the same medicine

Status: a rule, and an audit of it (`scripts/audit_groups.py`, output in `data/audit/`). The site uses it for one thing: a medicine page (`medicines.html?id=<group id>`, `scripts/medicine_pages.py`) for each group with `first_release_candidate`. The page lists the packages of the group that have a shortage notice in the archive. All other packages keep their package pages.

A medicine group is a set of register packages with equal rule inputs. A group that is "unsure" gets no medicine page, and its packages stay package pages. A wrong group could lead to a wrong health-related claim, so the rule keeps packages apart whenever the register data does not show that they are equal. A missing identity makes a group unsure.

## Page contract

These rules bind every page built from a group.

- The public page indexes **reported shortages** and keeps **package-level source facts**: each package row shows its own VNR, its own register fields, its own shortage notice and its own source.
- A group says: these packages have equal register fields (substances, strength text, form, route, ATC, device). It says nothing else.
- Never infer substitution, pharmacy stock, availability, or the history of a group from group membership. Do not write that one package can replace another, and do not write that a group "has an alternative".
- Fimea's own substitution information (the group code `Substituutioryhma`) stays attached to its exact package and its source. It is shown for that package only, never for the group.
- The audit counts "same-key packages": packages with the same rule inputs. These counts compare two internal rules. They are not public claims about availability or interchangeability, and no page may quote them.
- A group has no history. Group membership is built from today's register. It must not be read back in time.

## Data

Fimea's basic register (`Perusrekisteri`), in the form `scripts/build.py` reads. The shortage file only decides which groups are "in the current shortage". The audit day is the register's run date (`Ajopvm`). The pair used is matched: register run date 2026-11-24 and the shortage capture 2026-11-24 (Fimea file time Mon, 23 Nov 2026 23:20:01 GMT). `data/audit/summary.json` records the names, dates, sizes and SHA-256 of the register and of the shortage file used, and the SHA-256 of `groups.json`. The register file is 225 MB and is not in the repository; `scripts/fetch_register.py` downloads it.

## The rule

Two register packages (packages with a VNR) are in one group when all of these are equal:

| Input | Register field | How it is compared |
| --- | --- | --- |
| Species | `VET`, or an ATC code that starts with Q | human or veterinary; for veterinary also the target species (`Kohdeelainlaji`) |
| Active substances | `Pakkaus_Laakeaine` → `Laakeaine` → `VaikuttavaAine/Aine` (id and name) | The whole set. A combination product needs every substance. The order does not matter. A different salt, ester or hydrate is a different substance (another `Aine` id). |
| Strength text | `Vahvuus` of the product | The text only, with case, spaces and the decimal separator made equal and trailing zeros removed: `0,50 mg` equals `0.5 MG`. Units are not converted. For a combination the whole text is compared. |
| Form | `Laakemuoto` | The form id. Film-coated, plain, modified-release, pre-filled pen and cartridge are all different forms. |
| Route | `Antoreitti` | The whole set of route ids. |
| ATC code | `ATC-koodi` | The full code. |
| Device | `Annostelulaite` of the package | The device id, or none. |
| Presentation (injectable and device-bearing forms only) | `Sailytysastia` (immediate container) and `Pakkauskoko` with its unit | The container id and the size of **one unit**: one vial, ampoule, syringe, pen, cartridge or bag. See below. |

Not inputs: brand name, holder, pack count, total pack volume, pack text, VNR, and the register's substitution group code. A box, a blister, a jar or a tube of a form that is not injectable or device-bearing is not a difference of presentation.

**The strength text is text.** The register does not say which part of `8 mg / 2.5 mg` belongs to which substance. For Caninda (110560, 450435) the text lists 8 mg first, but the register's composition gives 8 mg to candesartan cilexetil and 2.5 mg to indapamide, and the audit lists the substances in register id order, with indapamide first. The audit therefore prints the strength text beside the substance list and states that it is not mapped. A page may show strengths per component only after a verified mapping from the register composition on one basis. The first release does not.

**Strength comes from `Vahvuus`, not from the amounts in `Laakeaine`.** The basis of `Maara` in `Laakeaine` depends on the source. It is sometimes a total for the package (2 g of fluconazole in a 100 ml bag), sometimes not: Trexan pre-filled syringes of 0.3 ml and of 1.0 ml (562071, 456852) both give 25 mg. The amounts are often empty and are written in different units. They are never read as a per-unit strength, and a per-unit strength is never inferred from them. They are used only for the ratio check below.

### Presentation: container and size of one unit

Equal `Vahvuus` does not mean one presentation. Trexan group m4091940612e4 gave one strength text (25 mg/ml) and one product record to pre-filled syringes of 0.3, 0.4, 0.6, 0.8 and 1.0 ml; 562071 holds 7.5 mg per syringe and 456852 holds 25 mg (Fimea SmPC section 6). Celeston Chronodose 433078 is a 5 ml vial and 473507 is a 5 x 1 ml pack of ampoules.

For injectable forms (injection or infusion) and for device-bearing forms, the immediate container (`Sailytysastia`) and the size of one unit are rule inputs. The size of one unit is verified only when the register's pack text and its `Pakkauskoko` fields say the same: `5 x 1 ml` with size 1 and unit ml is a unit of 1 ml; the count in the text is dropped. A pack text that the fields do not explain (`4 x 5 ml` with size 1 and unit `kpl`, `10 x 6 x 1 ml`, `100 mg + 2 ml`), a pack with an extra pack factor, or a missing container is not verified and gives `presentation_not_verified`: the packages stay on package pages. The pack count and the total volume are never used.

A form is **device-bearing** when its name mentions a pre-filled pen or syringe, a cartridge, an injector, an inhaler or a spray (`esitäyt`, `kynä`, `ruisku`, `injektori`, `sylinteri`, `inhalaat`, `sumut`, `laite`), or when the package has a device id. The word "dose" alone (single-dose eye drops, `annosteltu` powders) names no device. A device-bearing package with no device id is an unknown device variant, and nothing independent in the register says it is the same variant as another. It gives `device_not_verified`, in a group of one product record as well as in a cross-product group. Only a device id in the register lifts it. The first release keeps these on package pages.

### One product record, or several

A register product record (`Laakevalmiste`) is the unit Fimea describes: a name, a strength, a form and a marketing authorisation. All packages of one record are one presentation. A group whose members come from **more than one product record** is a cross-product group, and it is judged by the register, not by the rule inputs alone. It is sure only when all of these hold. The product record is the boundary even when two records share a licence or when a licence is blank.

1. Every product has an authorisation identity: the EU number without its pack suffix (`EU-lupanumero`, for example `EU/1/99/119`), else the national number (`Lupanumero`). Both are read. A blank identity gives `authorisation_identity_missing`.
2. The current members have one register substitution code and every one of them has it (`register_group_disagrees`, `several_products_no_register_group`). The code is read for current members only: packages on the market on the register day or in the shortage file.
3. No member is biological or plasma-derived (`biological_several_products`). The audit has no list of biosimilars.
4. Every device-bearing member has a device id (`device_not_verified`, see Presentation). Liprolog KwikPen (517586) and Liprolog Junior KwikPen (544210) have no device id and are different product records, so they are not joined, also under one EU licence.
5. The composition check passes (next section).

### Composition check

Equal substances and equal strength text can hide other concentrations. Physioneal 35 and 40 Clear-Flex (016129 against 016111 and 016194) have the same glucose per ml and different calcium and lactate. The audit compares the amounts in `Laakeaine` independently of the strength text. Because the basis of the amounts depends on the source, only the ratios inside one package are compared: each amount is divided by the amount of the first substance (by register id). Mass units (g, mg, mikrog) are put in mg. Ratios may differ by 2 % (register rounding).

Result per group with more than one package and more than one substance: `verified`, `differs`, `incomplete` (an amount is empty or a range, units cannot be compared, an "expressed as" substance is given, or a substance is listed twice) or `not_applicable`.

- `differs` sets the flag `quantity_review` for manual review and gives `composition_differs` (any members, also off the market). Base, salt and unit conventions can differ in the register, so the flag does not say which package is wrong.
- A cross-product group with `differs` or `incomplete` is unsure (`composition_not_verified`). Complex mixtures stay on package pages unless the full composition is verified on one basis.
- Packages of one product record are one presentation, so `incomplete` alone does not make them unsure.

### Parallel imports and distributions

`RinnakkaisTuonti` and `RinnakkaisJakelu` name a sales channel, not the original product. The register has no field that points from an import to its original. A parallel import or distribution joins the group of the original **only when its EU number (without pack suffix) equals the EU number of an original in the group**. Rybelsus (130247, EU/1/20/1430) and parallel-distributed Wegovy (074190, EU/1/21/1608) have equal inputs but different EU numbers, so Wegovy is a group of its own with `parallel_not_linked`, also for the 4 mg versions. A national parallel import has no EU number to link with, so it is always a group of its own. Equal names are not a link. The first release keeps unlinked imports on package pages.

## Deliberately not merged

Each of these gives two groups, even when the register's substitution group puts the packages together:

- Different salts, esters or hydrates of one base (`Quetiapine fumarate` and `Quetiapine hemifumarate`).
- Different strength texts, also when one is a starter pack with two strengths.
- Different forms, routes, devices and ATC codes.
- Strengths written in other units (`500 mikrog` and `0.5 mg`). The audit does not look for these pairs. This is the one place where a group can be smaller than it needs to be.
- Human and veterinary products.
- Products from different product records unless the register backs them as above.
- Injectables in other immediate containers (vial and ampoule) or with another size of one unit, and device-bearing packages without a device id.
- A parallel import that is not linked by an EU number.

The register's substitution groups are wider. On 23 Nov 2026, 612 of its 1685 group codes contain more than one medicine group: they differ in substance (131 codes), form (146), presentation (153), device (60), strength text (56) and route (38).

## Unsure: no medicine page

A group can have several reasons. The package pages stay.

| Reason | What it means |
| --- | --- |
| `veterinary` | A veterinary product. Species, withdrawal periods and doses differ. |
| `no_marketing_authorisation_record` | A product has no marketing authorisation record. |
| `no_substance_listed` | The register lists no active substance. |
| `strength_not_stated` | `Vahvuus` is empty. The amounts cannot replace it. |
| `route_not_stated` | The product has no route. The form alone does not say it. |
| `product_substances_inconsistent` | The packages of one product list different substances. |
| `vnr_listed_twice` | The VNR is on two register records, so it cannot be placed. |
| `register_group_disagrees` | The current members have different register codes, or some have none. |
| `several_products_no_register_group` | More than one current product record and no register code. |
| `biological_several_products` | A biological or plasma-derived product from more than one product record. |
| `authorisation_identity_missing` | A product in a cross-product group has neither an EU nor a national authorisation number. |
| `device_not_verified` | A device-bearing package has no device id: the device variant is unknown. |
| `presentation_not_verified` | An injectable or device-bearing package has no container, or the size of one unit cannot be verified from the register's pack fields. |
| `composition_differs` | The composition check found other ratios between members. Flagged for manual review. |
| `composition_not_verified` | A cross-product group whose composition is `differs` or `incomplete`. |
| `parallel_not_linked` | A parallel import or distribution with no EU number shared with an original. |

A single package is a group of one. It cannot be unsure for reasons that compare packages (`register_group_disagrees`, `several_products_no_register_group`), but it can be unsure for its own data: a missing route (`route_not_stated`), a missing strength, a veterinary product, an unverified presentation, a missing device id, or a VNR that is on two records.

## VNR attribution and counts

- A VNR can be on two register records (a package entered again under a new product). On 23 Nov 2026 there are 54. A group that holds one is unsure, and in the summary the VNR is **ambiguous**: it is not given to either group, and the shortage VNRs 018486 (Topimax), 370212 (Mirena) and 424765 (Haemate) are left out of the confident count (753 of 756).
- The shortage VNR is joined by its current VNR, else by an old VNR, as the build does. The summary says how many were joined by an old VNR (4).
- "On the market" in the audit means: the register flag `Kaupan` is 1 and the market entry and exit dates agree. Eight packages are on the market by their dates while the flag is not 1 (006334, 056292, 161756, 196986, 414779, 425281, 464436, 540878). They are listed in the summary and not counted.

## First release

The first release uses only **verified single product presentations**. In the audit this is `first_release_candidate`: the group has no unsure reason and all its members come from one product record, so they share the container and the verified size of one unit, and the device id where a device is named. Each package row keeps its own shortage notices, its own sources and its own history. The group page has no history of its own and states no substitute or stock claim: membership only says that the register fields above are equal.

**Container guard.** A group of several packages is eligible only when all members have the same known immediate container id (`Sailytysastia`; `container_verified` in the audit). One product record can hold a tube and a pump bottle with equal fields and no device id (Zovirax cream 081243 and 081252, container ids 14 and 11); a blank container is not known. When the guard fails, every member keeps its package page. The guard is an eligibility check only: it adds no unsure reason and does not change which packages are in one group. A group of one package has nothing to compare.

Everything else stays on package pages: cross-product groups, unverified identity, authorisation links, parallel imports, component strengths, injectables whose unit size is not verified, and device variants without a device id.

## Checks in the audit

For every group the audit checks the raw fields of its members again, apart from the key: `merges_different_substance`, `merges_different_strength`, `merges_different_form` and `merges_different_route` must be false. They are false for all groups. The review cases are in `data/audit/examples.md` and in `tests/test_audit_groups.py`, which also checks them on the real register when it is present.

## Open points

1. Salts: `fumarate` and `hemifumarate` are apart. Joining them needs a reviewed list of salt pairs.
2. Strength spelling in other units gives two groups. This can only lower the number of packages found together.
3. The composition tolerance (2 %) and the list of device words are judgements. The audit reports the groups that depend on them.
4. 70 old VNRs are also the current VNR of another package; the current one wins in the shortage join.
