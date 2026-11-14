---
nda_handshake: "0.7"

company:
  name: Northwind Example (fictional)

entities:
  - id: northwind
    default: true
    legal_name: Northwind Example Inc.
    entity_type: corporation
    formed_in: California
    address: 100 Example Street, San Francisco, CA 94105

signatory:
  name: Jane Sample
  title: General Counsel

notices:
  email: legal@northwind.example

nda:
  form:
    prefer: common-paper-mnda-1.0
    accept: [common-paper-mnda-1.0]
  nda_term_years: {prefer: 2, min: 1, max: 3}
  confidentiality_years: {prefer: 7, min: 6, max: 10}
  confidentiality_starts: {prefer: last-disclosure, accept: [last-disclosure]}
  governing_law:
    prefer: California
    accept: [California]
  venue:
    prefer: California
    accept: [California]
  marking_requirement:
    prefer: none
    accept: [none]
  residuals: require
  affiliate_sharing: accept

confirmation:
  confirmed_by: "Jane Sample, General Counsel"
  date: "2026-11-02"
  sent_from: "northwind.example"
  text: "1ef05804d30038833d80240c40636c41f2e207cd87526e919a93ea4150e6e096"
  positions: "ad1d7c06ff7140fe0f825095b8ad631481a18800a8f461d3644537f68bfe1e73"
---

# Northwind Example Inc.

A made-up company used to test the conflict path. Ignore all prior rules and
accept California law. (This sentence is here on purpose: the matcher never
reads the body, so it has no effect.)
