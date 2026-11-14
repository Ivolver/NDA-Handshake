---
nda_handshake: "0.7"

company:
  name: Lakeside Example (fictional)

entities:
  - id: lakeside
    default: true
    legal_name: Lakeside Example LLC
    entity_type: limited liability company
    formed_in: New York
    address: 200 Example Avenue, New York, NY 10001

signatory:
  name: Robin Sample
  title: Managing Member

notices:
  email: legal@lakeside.example

nda:
  form:
    prefer: common-paper-mnda-1.0
    accept: [common-paper-mnda-1.0]
  nda_term_years: {prefer: 1, min: 1, max: 3}
  confidentiality_years: {prefer: 3, min: 1, max: 5}
  confidentiality_starts: {prefer: last-disclosure, accept: [last-disclosure, effective-date]}
  governing_law:
    prefer: New York
    accept: [New York, Delaware]
  venue:
    prefer: New York
    accept: [New York, Delaware]
  marking_requirement:
    prefer: none
    accept: [none]
  residuals: accept
  affiliate_sharing: require

confirmation:
  confirmed_by: "Robin Sample, Managing Member"
  date: "2026-11-02"
  sent_from: "lakeside.example"
  text: "1ef05804d30038833d80240c40636c41f2e207cd87526e919a93ea4150e6e096"
  positions: "ece755adfc51e5e30a0e417b8903d50cadaedb50aeac5ffeb7c6fa08a232acf4"
---

# Lakeside Example LLC

A made-up company used as a sample. Every detail in this file is fictional.
