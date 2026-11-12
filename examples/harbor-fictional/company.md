---
company_md: "0.1"

company:
  name: Harbor Example (fictional)
  website: https://harbor.example

entities:
  - id: harbor
    default: true
    legal_name: Harbor Example LLC
    entity_type: limited liability company
    formed_in: Delaware
    address: 1 Example Plaza, Suite 100, Miami, FL 33131

signatory:
  name: Alex Sample
  title: Chief Executive Officer

notices:
  email: legal@harbor.example

nda:
  form:
    prefer: common-paper-mnda-1.0
    accept: [common-paper-mnda-1.0, bonterms-mnda-1.0]
  type:
    prefer: mutual
    accept: [mutual]
  nda_term_years: {prefer: 1, min: 1, max: 2}
  confidentiality_years: {prefer: 2, min: 2, max: 5}
  governing_law:
    prefer: Delaware
    accept: [Delaware, New York, Florida]
  venue:
    prefer: Delaware
    accept: [Delaware, New York, Florida]
  riders:
    residuals: reject
    affiliate_sharing: accept
    non_solicit: reject
---

# Harbor Example LLC

A made-up company used as a sample. Every detail in this file is fictional.
