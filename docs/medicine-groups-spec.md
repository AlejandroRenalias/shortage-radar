# Medicine groups: what makes two packages the same medicine

Status: a rule for review, and an audit of it (`scripts/audit_groups.py`, output in `data/audit/`). Nothing on the site uses it yet.

A medicine group is a set of register packages with equal rule inputs. A package in a group that is "unsure" gets no medicine page and stays a package page. A wrong group could lead to a wrong health-related claim, so the rule keeps packages apart whenever the register data does not show that they are equal.

A group states a fact about register data: these packages have the same substances, strength, form and route. It does not say what a person, a doctor or a pharmacy can do with them. No page may add that.

## Data

Only Fimea's basic register (`Perusrekisteri`), in the form `scripts/build.py` reads. The shortage file only decides which groups are "in the current shortage". The day of the audit is the register's run date (`Ajopvm`).

## The rule

Two register packages (packages with a VNR) are in one group when all of these are equal:

| Input | Register field | How it is compared |
| --- | --- | --- |
| Species | `VET`, or an ATC code that starts with Q | human or veterinary; for veterinary also the target species (`Kohdeelainlaji`) |
| Active substances | `Pakkaus_Laakeaine` → `Laakeaine` → `VaikuttavaAine/Aine` (id and name) | The whole set. A combination product needs every substance. The order does not matter. A different salt, ester or hydrate is a different substance (it has another `Aine` id). |
| Strength | `Vahvuus` of the product | The text, with case, spaces and the decimal separator made equal and trailing zeros removed: `0,50 mg` equals `0.5 MG`. Units are not converted. For a combination the whole text is compared, so `50 mg / 200 mg` differs from `25 mg / 100 mg`. |
| Form | `Laakemuoto` | The form id. Film-coated, plain, modified-release, pre-filled pen and cartridge are all different forms. |
| Route | `Antoreitti` | The whole set of route ids. `Laskimoon` differs from `Laskimoon, Lihakseen`. |
| ATC code | `ATC-koodi` | The full code. |
| Device | `Annostelulaite` of the package | The device id, or none. A package with a dosing syringe and a package with a pipette are apart. |

The strength comes from the product's `Vahvuus`, not from the amounts in `Laakeaine`. Those amounts are totals for the package (2 g of fluconazole in a 100 ml bag, 3.2 mg in a 3 ml pen of `2.4 mg`), are often empty, and are written in different units.

These do not separate packages, so they are not inputs: brand name, marketing authorisation holder, pack size and pack text, VNR, and the register's own substitution group code (`Substituutioryhma`). The group code is used as a check (see "unsure").

### Parallel imports

A parallel import or parallel distribution (`RinnakkaisTuonti`, `RinnakkaisJakelu` of the marketing authorisation) has its own product record and often the original's name. It joins the group of the original when all inputs are equal, and the group lists its VNRs apart (`parallel_import`, `parallel_distribution`). A parallel import of another strength or form is not joined. Several parallel imports of one product do not make a group unsure.

## Deliberately not merged

Each of these gives two groups, even when the register's substitution group puts the packages together:

- Different salts, esters or hydrates of one base (`Quetiapine fumarate` and `Quetiapine hemifumarate`).
- Different strengths, also when one of them is a starter pack with two strengths.
- Different forms: tablet and film-coated tablet, capsule and tablet, a cartridge and a pre-filled pen.
- Different routes, also when one product lists one more route than another.
- Different devices on the package.
- Different ATC codes (14 sets of equal substances, strength and form have two).
- Strengths written in different units (`500 mikrog` and `0.5 mg`) or in different words. The audit does not try to find these pairs; it keeps them apart. This is the one place where a group can be smaller than it needs to be.
- Human and veterinary products.

The register's substitution groups are wider. On 23 Nov 2026, 363 of its 1685 group codes contain more than one medicine group: they differ in substance (131 codes, the salts and hydrates above), form (147), device (60), strength (57) and route (47). The current impact levels use the register's code. See `data/audit/summary.md`.

## Unsure: no medicine page

A group is unsure when any of these holds. A group can have several reasons. The checks of the register's group code and of marketing authorisations look at current members only (on the market on the register day, or in the current shortage file), so a package that left the market years ago does not make a group unsure.

| Reason | What it means |
| --- | --- |
| `veterinary` | A veterinary product. Species, withdrawal periods and doses differ, and the register has no substitution groups for them. |
| `no_marketing_authorisation_record` | A product has no marketing authorisation record in the register. |
| `no_substance_listed` | The register lists no active substance. |
| `strength_not_stated` | `Vahvuus` is empty (combination packs, kits, nutrition products, vaccines). The amounts in `Laakeaine` cannot replace it. |
| `route_not_stated` | The product has no route. The form alone does not say it. |
| `product_substances_inconsistent` | The packages of one product list different substances. |
| `register_group_disagrees` | The current members have different register group codes, or some have a code and some have none. The register and this rule disagree, so no claim is made. |
| `several_products_no_register_group` | The current members come from more than one marketing authorisation (parallel imports and distributions not counted) and none has a register group code. The register has not said the products belong together. |
| `biological_several_products` | A biological or plasma-derived product with more than one marketing authorisation (originator and biosimilar, for example), even when the register has a group code. |
| `vnr_listed_twice` | The VNR is on two register packages (a package entered again under a new product), so it cannot be placed. |

A single package on its own is a group of one and is not unsure. It has no other packages to show.

## Checks in the audit

For every group the audit checks the raw fields of its members again, apart from the key: `merges_different_substance`, `merges_different_strength`, `merges_different_form` and `merges_different_route` must be false. On 23 Nov 2026 all four are false for all 7899 groups. The group id is a hash of the rule inputs, so the same inputs give the same id in later runs. A change in the register that changes an input (a new `Vahvuus` text) changes the id.

## Open points for the review

1. Salts: the rule keeps `fumarate` and `hemifumarate` apart. Fimea's code joins them. Joining them needs a reviewed list of salt pairs.
2. Strength spelling: the same strength in two spellings (`0.5 mg`, `500 mikrog`) gives two groups. This can only lower the number of other packages found, so a medicine can be shown with no other package when one exists.
3. Unsure reasons that hide many packages: `strength_not_stated` and `register_group_disagrees` (some members without a code).
4. Old VNRs: a shortage VNR is joined to a package by its current VNR, else by an old VNR (as the build does). 70 old VNRs are also the current VNR of another package; the current one wins.
