# Data Features Verification (Task B5)

> **Date:** 2026-10-25 — verified against the live server (real database, real rows).

Checked endpoints that the teacher dashboard and reports depend on.

---

## 1. Student history pagination — `GET /attendance/student/{id}`

| Request | `X-Total-Count` | Rows returned | Verdict |
|---|---|---|---|
| `/attendance/student/8?limit=2&offset=0` | `12` | 2 (newest first) | ✅ |
| `/attendance/student/8?limit=2&offset=2` | `12` | 2 (next page) | ✅ |

Sample row (newest first, correct ordering):

```json
{"id":12,"student_id":8,"schedule_id":14,"check_type":"end","confidence":0.7212,
 "wifi_verified":1,"status":"verified","timestamp":"2026-10-25 11:42:22",
 "class_name":"abc","room":"Ruang Demo 105"}
```

Notes:
- `X-Total-Count` reports the **unfiltered-by-page** total (12), as the dashboard needs for paging.
- Rows are ordered newest-first; joined `class_name`/`room` are present.
- `timestamp` is a local (CST) wall-clock string, consistent with the schedule fix.

## 2. CSV export — `GET /attendance/export/csv?date=YYYY-MM-DD`

| Check | Result |
|---|---|
| `Content-Type` | `text/csv; charset=utf-8` ✅ |
| Header row | `id,timestamp,check_type,confidence,wifi_verified,status,student_id,student_name,nim,schedule_id,class_name,room` ✅ |
| Date filter | `date=2026-10-25` returned only that day's rows ✅ |
| Values | `wifi_verified` rendered as `yes/no`; `confidence` as full float; `timestamp` as `YYYY-MM-DD HH:MM:SS` (local) ✅ |
| Opens in spreadsheet | columns parse correctly (comma-separated, no stray separators) ✅ |

Sample rows:

```
7,2026-10-25 08:12:05,start,0.8243706226348877,yes,verified,8,Buchari,F25040126,11,Demo Interactive,Ruang Demo 334
8,2026-10-25 08:12:31,end,0.9545847177505493,yes,verified,8,Buchari,F25040126,11,Demo Interactive,Ruang Demo 334
```

## 3. Follow-ups (non-blocking)

- `confidence` is exported with full float precision (17 digits). Cosmetic; if the school
  report needs nicer numbers, round to 4 decimals in the export query.
- CSV `timestamp` has no timezone suffix but is documented as local (CST) wall clock.
  A note in the deployment guide is enough; no code change required for the pilot.
