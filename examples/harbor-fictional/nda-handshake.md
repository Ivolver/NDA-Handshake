---
nda_handshake: "0.7"

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
  custom_terms_required: false
  form:
    prefer: common-paper-mnda-1.0
    accept: [common-paper-mnda-1.0]
  nda_term_years: {prefer: 1, min: 1, max: 2}
  confidentiality_years: {prefer: 2, min: 2, max: 5}
  confidentiality_starts: {prefer: effective-date, accept: [effective-date, last-disclosure]}
  governing_law:
    prefer: Delaware
    accept: [Delaware, New York, Florida]
  venue:
    prefer: Delaware
    accept: [Delaware, New York, Florida]
  marking_requirement:
    prefer: none
    accept: [none, written-marked]
  residuals: reject
  affiliate_sharing: accept

confirmation:
  confirmed_by: "Alex Sample, Chief Executive Officer"
  date: "2026-11-02"
  sent_from: "harbor.example"
  text: "1ef05804d30038833d80240c40636c41f2e207cd87526e919a93ea4150e6e096"
  positions: "9ef2c42eb6ec310386d7ab328dfec1dad4ad8ee93e4d9043bcc8a04afa84036c"
---

# Harbor Example LLC

A made-up company used as a sample. Every detail in this file is fictional.
