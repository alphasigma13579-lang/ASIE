# Source Priority, Freshness, and Fallback Policy

## سياسة أولوية المصادر وحداثتها وبدائل الفشل

## Priority Order

## ترتيب الأولوية

1. Exact Saudi official open datasets/APIs with compatible public-reuse terms.
2. Exact open datasets/APIs from official international or institutional publishers.
3. Fresh approved open-data cache carrying the original source ledger.
4. Reference-only link shown to the user without backend retrieval.

Licensed APIs, registered APIs, marketplaces, general public web pages, and agreement-based data sharing are not fallback sources under `strict_open_data_only_v1`.

## Freshness Policy

## سياسة الحداثة

| Evidence Type | Arabic | Freshness Target |
| --- | --- | --- |
| Prices | الأسعار | 1-14 days |
| Tender opportunities | المناقصات والفرص | 1-7 days |
| Regulations | اللوائح | 1-30 days or change-detected |
| Economic indicators | المؤشرات الاقتصادية | according to release cycle |
| Sector reports | تقارير القطاعات | 0-24 months |
| Similar cases | التجارب المشابهة | 0-36 months preferred |
| Product analytics | تحليلات المنتج | near-real-time to daily |

## Fallback Policy

## سياسة البدائل

| Failure | Arabic | Fallback |
| --- | --- | --- |
| Official API unavailable | API رسمي غير متاح | Use cached evidence if fresh, otherwise mark unavailable |
| Open resource unavailable | المصدر المفتوح غير متاح | Use fresh approved cache or mark unavailable; do not switch to crawling |
| Reference-only target unavailable | الرابط المرجعي غير متاح | Show link state; backend must not probe it |
| Pinecone cache stale | كاش Pinecone قديم | Trigger source adapter refresh |
| Discovery finds non-open source | اكتشاف مصدر غير مفتوح | Classify reference-only or blocked; do not fetch |

## User Display Rule

## قاعدة العرض للمستخدم

If data is missing, stale, or blocked, show the state clearly instead of inventing.

إذا كانت البيانات ناقصة أو قديمة أو محجوبة، تعرض الحالة بوضوح بدل الاختراع.
