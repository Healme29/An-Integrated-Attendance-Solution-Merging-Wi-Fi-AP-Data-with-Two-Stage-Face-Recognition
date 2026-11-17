# Felix 22.0 — Attendance Sheet

Felix 22.0 upgrades the Teacher Dashboard's former **Students** page into a class-based **Attendance Sheet**. It keeps the complete enrolled roster visible whether students attended or not, while separating the roster view from attendance-time records.

## What was added

- **Attendance Sheet** replaces the **Students** item under Management.
- Every schedule (class/subject) has its own enrolled student roster.
- A date selector shows the attendance result for one class session.
- **Student List** shows every student registered for the selected class:
  - Green check: the student submitted at least one attendance check for that class and date.
  - Red X: the student submitted no attendance check for that class and date.
- **Attendance Record** lists students who submitted attendance and opens a time-details dialog.
- The time-details dialog shows the student name, start-attendance time, and end-attendance time.
- **Add Student** creates a student and enrolls them in the selected class.
- **Import CSV** bulk-creates or reuses students and enrolls them in the selected class.
- **Export Excel** downloads the complete roster and attendance result as a formatted `.xlsx` file.
- Removing a student from a class removes only the class enrollment. The global student profile and attendance history are preserved.

## What it looks like

The Attendance Sheet page has one control row:

1. Class / subject selector
2. Attendance date
3. Student search
4. Add Student
5. Import CSV
6. Export Excel

Below the controls are two tabs:

- **Student List** — full class roster with attendance check or absent X.
- **Attendance Record** — submitted attendance only, with a **View Times** button.

The page summary displays the number enrolled, attended, and absent.

## How to use it

### View a class attendance sheet

1. Open **Management → Attendance Sheet**.
2. Select the class / subject.
3. Select the class date.
4. Read the full roster in **Student List**.
5. Use **Attendance Record** to inspect submitted start/end times.

### Add one student manually

1. Select the class / subject.
2. Select **Add Student**.
3. Confirm the class, then enter full name, NIM, and optional MAC address.
4. Select **Save**.

### Import a CSV roster

1. Select the destination class / subject.
2. Select **Import CSV**.
3. Choose a UTF-8 CSV file with these columns:

```csv
name,nim,mac_address
Ali,A001,AA:BB:CC:DD:EE:01
Budi,B002,
```

`name` and `nim` are required. `mac_address` is optional. Existing NIMs are reused and enrolled instead of duplicated.

### Export the attendance sheet

1. Select the class / subject and date.
2. Select **Export Excel**.
3. Open the downloaded `.xlsx` file in Microsoft Excel or another compatible spreadsheet application.

The workbook includes every enrolled student, present/absent result, attendance status, start time, end time, class/subject, and date. Present rows are green and absent rows are red.

## Data safety

- Existing students and schedules are migrated into the roster system once.
- Existing attendance rows remain unchanged.
- Class removal does not delete the global student profile or attendance history.
- Felix 22.0 has automated coverage for roster status, CSV import, Excel export, and class-only removal.
