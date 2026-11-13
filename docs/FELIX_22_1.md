# Felix 22.1 — Dashboard Efficiency and Schedule CSV Tools

Felix 22.1 refines the Teacher Dashboard introduced in Felix 22.0. It removes duplicate Attendance Sheet labels, modernizes the date control, and adds bulk schedule import/export.

## Improvements

### Cleaner Attendance Sheet

- Removed the repeated “Class roster and attendance status” subtitle.
- Removed the redundant card header that repeated “Student List” or “Attendance Record” and the selected-class prompt.
- Kept both functional tabs, their tables, status indicators, and attendance-time details.
- Reduced vertical space so teachers reach the roster faster.

### Modern attendance date control

- Added a compact card-style date control with a calendar icon and “Attendance date” label.
- Added modern focus, hover, border, and shadow states.
- Retained the operating system's native date calendar for accessibility and reliable date entry.

### Schedule CSV import and export

The Schedules page now includes **Import CSV** and **Export CSV** beside **Add Schedule**.

Import files must contain:

```csv
class_name,day,start_time,end_time,room,ap_bssid
Algorithms,Monday,08:00,09:30,Lab 1,AA:BB:CC:DD:EE:10
Databases,2,10:00,11:30,Lab 2,
```

- `class_name`, `start_time`, and `end_time` are required.
- Use either `day` or `day_of_week`.
- `day` accepts Monday through Sunday.
- `day_of_week` accepts `0` (Monday) through `6` (Sunday).
- `room` and `ap_bssid` are optional.
- Invalid rows, duplicate schedules, and room/time conflicts are skipped and reported.
- Export downloads all schedules in the same reusable UTF-8 CSV structure.

## Verification

Felix 22.1 includes automated tests for schedule import, duplicate handling, export output, the Felix 22.0 attendance-sheet features, and all pre-existing backend behavior.
