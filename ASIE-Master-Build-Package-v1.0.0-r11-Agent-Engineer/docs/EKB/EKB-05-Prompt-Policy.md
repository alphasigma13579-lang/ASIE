# EKB-05 — Prompt Policy

## القاعدة

البرومبت لا يحمل معرفة المشروع. البرومبت يحدد المهمة، ويأمر Agent بقراءة EKB والوثائق المطلوبة.

## مستويات البرومبت

### 1. Constitution Prompt

ثابت، قصير، يحدد القيود:

```text
أنت Principal Software Engineer يعمل على ASIE.
التزم بـEKB كمصدر قراءة.
لا تكسر AAS Freeze.
لا تنشئ Runtime موازي.
لا تتجاوز Bus/Socket/Module Runtime.
لا تفعل AI Provider أو network fetch.
عند التعارض توقف وبلّغ.
```

### 2. Task Prompt

خاص بالمهمة فقط:

```text
نفذ <المهمة>.
اقرأ <ملفات EKB/وثائق المصدر>.
عدّل فقط <المسارات>.
لا تعدل <المسارات المجمدة>.
شغّل <الاختبارات>.
أخرج تقريرًا مختصرًا.
```

### 3. Context

الملفات والوثائق المطلوبة للمهمة، وليس كل المشروع.

## ما لا يدخل البرومبت

| المعرفة | مكانها الصحيح |
|---|---|
| قواعد DIB | `domains/DIB/` |
| المتوسطات السوقية | `domains/Engines/Market-Estimation-Engine.md` |
| Monte Carlo | `domains/Engines/Monte-Carlo-and-Sensitivity.md` |
| Decision Council | `domains/Engines/Decision-Council.md` |
| Dashboard | `domains/Product/Dashboard-Command-Center.md` |
| Launch Guide | `domains/Product/Project-Launch-Guide.md` |
| National Economic Intelligence | `domains/Engines/National-Economic-Intelligence.md` |
| Strategic Alignment Score | `domains/Engines/Strategic-Alignment-Score.md` |
