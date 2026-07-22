# ACR-AIA-03 — Strategic Intelligence Foundation

## الحالة

`OFFLINE_REFERENCE_IMPLEMENTED` — طبقة Vision 2030 المرجعية فقط. لا World Bank/IMF/OECD، ولا مصادر خارجية أو AI أو مؤشرات وطنية حية.

## الضمانات

- كل Signal يتطلب المصدر والحداثة والجغرافيا والقطاع والثقة والنسب lineage والمراجعة.
- Vision 2030 لا ينتج Verdict أو أرقاماً مالية.
- Global/National يعيدان `DISABLED` مع external fetch مغلقين حتى ACR-AIA-04.
- الإخراج deterministic ومربوط بـhash، ولا يدخل Snapshot أو Decision Council v1.
