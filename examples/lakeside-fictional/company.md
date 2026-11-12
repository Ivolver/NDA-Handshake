---
company_md: "0.1"

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
  type:
    prefer: mutual
    accept: [mutual, one-way]
  nda_term_years: {prefer: 1, min: 1, max: 3}
  confidentiality_years: {prefer: 3, min: 1, max: 5}
  governing_law:
    prefer: New York
    accept: [New York, Delaware]
  venue:
    prefer: New York
    accept: [New York, Delaware]
  riders:
    residuals: accept
    affiliate_sharing: accept
    non_solicit: reject
---

# Lakeside Example LLC

A made-up company used as a sample. Every detail in this file is fictional.
