---
nda_handshake: "0.7"

company:
  name: Midtown Example (fictional)

entities:
  - id: midtown
    default: true
    legal_name: Midtown Example Inc.
    entity_type: corporation
    formed_in: New York
    address: 400 Example Square, New York, NY 10018

signatory:
  name: Casey Sample
  title: General Counsel

notices:
  email: legal@midtown.example

nda:
  form:
    prefer: common-paper-mnda-1.0
    accept: [common-paper-mnda-1.0]
  nda_term_years: {prefer: 2, min: 1, max: 3}
  confidentiality_years: {prefer: 3, min: 2, max: 5}
  confidentiality_starts: {prefer: effective-date, accept: [effective-date, last-disclosure]}
  governing_law:
    prefer: Delaware
    accept: [Delaware, New York]
  venue:
    prefer: Delaware
    accept: [Delaware, New York]
  marking_requirement:
    prefer: none
    accept: [none]
  residuals: accept
  affiliate_sharing: accept

confirmation:
  confirmed_by: "Casey Sample, General Counsel"
  date: "2026-11-02"
  sent_from: "midtown.example"
  text: "1ef05804d30038833d80240c40636c41f2e207cd87526e919a93ea4150e6e096"
  positions: "f9a6886056cd2beacb1137acd34a47856a37c15f371fa8e7b3820e61565a558b"
---

# Midtown Example Inc.

A made-up company used to test tie-breaking. It and Lakeside Example LLC are
both formed in New York, so a tie between Delaware and New York goes to New
York. Every detail in this file is fictional.
