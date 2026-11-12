---
nda_handshake: "0.4"

company:
  name: Outlier Example (fictional)

entities:
  - id: outlier
    default: true
    legal_name: Outlier Example Corp.
    entity_type: corporation
    formed_in: Texas
    address: 300 Example Boulevard, Austin, TX 78701

signatory:
  name: Sam Sample
  title: Chief Legal Officer

notices:
  email: legal@outlier.example

nda:
  custom_terms_required: true
---

# Outlier Example Corp.

A made-up company used to test the out-of-protocol path. It needs terms the
protocol excludes, so it flags every NDA for ordinary negotiation.
