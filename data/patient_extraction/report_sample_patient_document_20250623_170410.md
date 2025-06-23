# Patient Information Report

**Source Document:** sample_patient_document.txt  
**Extraction Date:** 2025-06-23 17:04:10  
**Schema Used:** demo_patient_intake

## Extracted Patient Data

### Demographics

* **Patient First Name:** John (confidence: 0.9) ✅
* **Patient Last Name:** Doe (confidence: 0.9) ✅
* **Patient Date Of Birth:** 01/15/1985 (confidence: 0.9) ✅
* **Prescriber Name:** Dr. Smith (confidence: 0.9) ✅
* **Requested Drug Name:** UNCLEAR: diabetes medication (confidence: 0.8) ⚠️
* **Pharmacy Name:** *[NOT FOUND]* ❌

### Contact Information

* **Prescriber Phone:** *[NOT FOUND]* ❌

### Medical Information

* **Primary Diagnosis Code:** *[NOT FOUND]* ❌
* **Primary Diagnosis Description:** Type 2 Diabetes, Hypertension (confidence: 0.9) ✅
* **Previous Medications Tried:** *[NOT FOUND]* ❌

### Insurance Information

* **Member Id:** BC123456789 (confidence: 0.9) ✅

### Other Information

* **Prescriber Npi:** *[NOT FOUND]* ❌
* **Requested Strength:** *[NOT FOUND]* ❌
* **Quantity Requested:** *[NOT FOUND]* ❌
* **Days Supply:** *[NOT FOUND]* ❌
* **A1C Value:** 7.2 (confidence: 0.9) ✅
* **Bmi Value:** *[NOT FOUND]* ❌
* **Contraindications Present:** *[NOT FOUND]* ❌
* **Priority Level:** *[NOT FOUND]* ❌
* **Clinical Justification:** Patient reports occasional headaches and requests refill of diabetes medication. Blood pressure well controlled on current medications. (confidence: 0.9) ✅

---

### Extraction Summary

* **Total Fields:** 20
* **Successfully Extracted:** 9
* **Success Rate:** 45.0%
* **Schema Used:** demo_patient_intake

*Report generated automatically by PatientDataExtractor*
