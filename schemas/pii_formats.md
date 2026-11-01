# Nigerian PII formats used by the generator and the detector regexes

| pii_type     | format                                   | example            |
|--------------|------------------------------------------|--------------------|
| NIN          | 11 digits                                | 12345678901        |
| BVN          | 11 digits, starts with 22                | 22123456789        |
| TIN          | 8 digits, hyphen, 4 digits (JTB style)   | 12345678-0001      |
| BANK_ACCOUNT | 10 digits (NUBAN)                        | 0123456789         |
| PASSPORT     | 1 letter + 8 digits                      | A12345678          |
| LICENCE_NO   | 3-letter state code + 5 digits + 2 letters + 2 digits | LAG12345AB67 |
| PHONE        | +234 then 10 digits, mobile prefixes 70x/80x/81x/90x/91x | +234 803 456 7890 |
| DOB          | DD/MM/YYYY                               | 14/03/1987         |
| ADDRESS      | street line, LGA, state (36 states + FCT)| 12 Adeola Odeku Street, Victoria Island / Eti-Osa / Lagos |

NIN and BVN are both 11 digits, so the detector must use the field label context
(OCR text to the left of the box) rather than the digit pattern alone to tell them apart.
