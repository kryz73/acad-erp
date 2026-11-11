import pytest

def test_attendance_sessions_and_marking(gql, admin_headers, faculty_headers, student1_headers):
    # 1. Create Attendance Session (Faculty allowed, Student blocked)
    create_sess = """
        mutation {
            createAttendanceSession(
                offeringId: 1,
                sessionDate: "2026-09-01",
                startTime: "09:00:00",
                endTime: "10:00:00",
                conductedBy: 1
            ) {
                id
                offeringId
                sessionDate
                startTime
                endTime
                conductedBy
            }
        }
    """
    # Student blocked
    _, errors = gql(create_sess, headers=student1_headers)
    assert errors is not None

    # Faculty allowed
    data, errors = gql(create_sess, headers=faculty_headers)
    assert errors is None
    sess_id = data["createAttendanceSession"]["id"]
    assert data["createAttendanceSession"]["offeringId"] == 1

    # 2. Query Offering Attendance Sessions
    q_sessions = "query { getOfferingAttendanceSessions(offeringId: 1) { id sessionDate startTime endTime } }"
    data, errors = gql(q_sessions, headers=student1_headers)
    assert errors is None
    assert any(s["id"] == sess_id for s in data["getOfferingAttendanceSessions"])

    # 3. Mark Attendance (Faculty only)
    # student 30
    mark_att = f"""
        mutation {{
            markAttendance(
                sessionId: {sess_id},
                studentId: 30,
                status: "Present"
            ) {{
                id
                studentId
                status
            }}
        }}
    """
    # Student blocked from marking attendance
    _, errors = gql(mark_att, headers=student1_headers)
    assert errors is not None

    # Faculty marks attendance
    data, errors = gql(mark_att, headers=faculty_headers)
    assert errors is None
    assert data["markAttendance"]["status"] == "Present"

    # Update attendance status (e.g., changed to Absent)
    mark_absent = f"""
        mutation {{
            markAttendance(
                sessionId: {sess_id},
                studentId: 30,
                status: "Absent"
            ) {{
                id
                status
            }}
        }}
    """
    data, errors = gql(mark_absent, headers=faculty_headers)
    assert errors is None
    assert data["markAttendance"]["status"] == "Absent"

    # 4. Query session attendance
    q_sess_att = f"query {{ sessionAttendance(sessionId: {sess_id}) {{ id studentId status }} }}"
    data, errors = gql(q_sess_att, headers=faculty_headers)
    assert errors is None
    assert any(r["studentId"] == 30 and r["status"] == "Absent" for r in data["sessionAttendance"])

def test_student_attendance_privacy_and_access(gql, admin_headers, faculty_headers, student1_headers, student2_headers):
    # student1 is id 30 (user_id 3), student2 is id 1 (user_id 12)

    # 1. Student1 queries own attendance -> Allowed
    q_self = "query { getMyAttendanceRecords(studentId: 30) { id studentId status } }"
    data, errors = gql(q_self, headers=student1_headers)
    assert errors is None
    assert isinstance(data["getMyAttendanceRecords"], list)

    # 2. Student1 queries Student2's attendance -> BLOCKED (Strict Privacy Constraint!)
    q_other = "query { getMyAttendanceRecords(studentId: 1) { id studentId status } }"
    data, errors = gql(q_other, headers=student1_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

    # 3. Faculty queries Student1 and Student2 -> Allowed
    data, errors = gql(q_self, headers=faculty_headers)
    assert errors is None
    data, errors = gql(q_other, headers=faculty_headers)
    assert errors is None

    # 4. Admin queries Student1 and Student2 -> Allowed
    data, errors = gql(q_self, headers=admin_headers)
    assert errors is None
    data, errors = gql(q_other, headers=admin_headers)
    assert errors is None

def test_low_attendance_detection_and_alerts(gql, admin_headers, faculty_headers, student1_headers):
    # Detect students below mandatory 75% attendance threshold
    q_low = "query { getLowAttendanceStudents(offeringId: 1, thresholdPct: 75.0) { studentId attendancePercentage } }"

    # Student blocked from querying low attendance list
    _, errors = gql(q_low, headers=student1_headers)
    assert errors is not None

    # Faculty allowed
    data, errors = gql(q_low, headers=faculty_headers)
    assert errors is None
    assert isinstance(data["getLowAttendanceStudents"], list)
    for student in data["getLowAttendanceStudents"]:
        assert student["attendancePercentage"] < 75.0

    # Admin allowed
    data, errors = gql(q_low, headers=admin_headers)
    assert errors is None
    assert isinstance(data["getLowAttendanceStudents"], list)
