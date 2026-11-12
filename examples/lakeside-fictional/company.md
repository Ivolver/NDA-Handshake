---
nda_handshake: "0.2"

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
  trade_secret_tail: accept
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
  existence_of_talks_confidential: accept
---

# Lakeside Example LLC

A made-up company used as a sample. Every detail in this file is fictional.
