import pytest

def test_exams_and_schedules_crud_and_rbac(gql, admin_headers, faculty_headers, student1_headers):
    # 1. Create Exam (Admin only)
    create_exam = """
        mutation {
            createExam(
                semesterId: 1,
                name: "Mid-Term Examination Oct 2026",
                examType: "Midterm",
                status: "scheduled"
            ) {
                id
                name
                examType
                status
            }
        }
    """
    # Student blocked
    _, errors = gql(create_exam, headers=student1_headers)
    assert errors is not None

    # Faculty blocked
    _, errors = gql(create_exam, headers=faculty_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(create_exam, headers=admin_headers)
    assert errors is None
    exam_id = data["createExam"]["id"]
    assert data["createExam"]["name"] == "Mid-Term Examination Oct 2026"

    # Query exams
    q_exams = "query { getExams(semesterId: 1) { id name examType } }"
    data, errors = gql(q_exams, headers=student1_headers)
    assert errors is None
    assert any(e["id"] == exam_id for e in data["getExams"])

    # 2. Create Exam Schedule (Admin only)
    create_sched = f"""
        mutation {{
            createExamSchedule(
                examId: {exam_id},
                courseId: 1,
                examDate: "2026-10-20",
                startTime: "09:30:00",
                endTime: "11:30:00",
                roomId: 1
            ) {{
                id
                examId
                courseId
                examDate
                startTime
                endTime
            }}
        }}
    """
    # Non-admin blocked
    _, errors = gql(create_sched, headers=student1_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(create_sched, headers=admin_headers)
    assert errors is None
    sched_id = data["createExamSchedule"]["id"]

    # Query exam schedules
    q_scheds = f"query {{ getExamSchedules(examId: {exam_id}) {{ id courseId examDate }} }}"
    data, errors = gql(q_scheds, headers=student1_headers)
    assert errors is None
    assert any(s["id"] == sched_id for s in data["getExamSchedules"])

    # Clean up
    gql(f"mutation {{ deleteExamSchedule(id: {sched_id}) }}", headers=admin_headers)
    gql(f"mutation {{ deleteExam(id: {exam_id}) }}", headers=admin_headers)

def test_exam_results_recording_and_privacy(gql, admin_headers, faculty_headers, student1_headers, student2_headers):
    # Exam schedule 1 was seeded for Course 1
    # Student 1 is student_id 30 (user_id 3)
    # Student 2 is student_id 1 (user_id 12)

    # 1. Record Exam Result (Faculty only)
    rec_res = """
        mutation {
            recordExamResult(
                examScheduleId: 1,
                studentId: 30,
                marksObtained: 84.5,
                isAbsent: false,
                isPublished: true
            ) {
                id
                examScheduleId
                studentId
                marksObtained
                isPublished
            }
        }
    """
    # Student blocked
    _, errors = gql(rec_res, headers=student1_headers)
    assert errors is not None

    # Faculty allowed
    data, errors = gql(rec_res, headers=faculty_headers)
    assert errors is None
    assert data["recordExamResult"]["marksObtained"] == 84.5

    # 2. Student 1 queries exam results for schedule 1 -> ONLY sees own result
    q_results = "query { getExamResults(examScheduleId: 1) { id studentId marksObtained } }"
    data, errors = gql(q_results, headers=student1_headers)
    assert errors is None
    results = data["getExamResults"]
    assert len(results) == 1
    assert results[0]["studentId"] == 30

    # 3. Student 2 queries exam results for schedule 1 -> ONLY sees own result
    data, errors = gql(q_results, headers=student2_headers)
    assert errors is None
    results = data["getExamResults"]
    assert len(results) == 1
    assert results[0]["studentId"] == 1

    # 4. Faculty queries exam results -> sees all student results
    data, errors = gql(q_results, headers=faculty_headers)
    assert errors is None
    assert len(data["getExamResults"]) > 1

    # 5. Admin queries exam results -> sees all student results
    data, errors = gql(q_results, headers=admin_headers)
    assert errors is None
    assert len(data["getExamResults"]) > 1
