import pytest

def test_programs_and_semesters_crud_and_rbac(gql, admin_headers, faculty_headers, student1_headers):
    # 1. Create Program (Admin only)
    create_prog = """
        mutation {
            createProgram(
                code: "MTECH_CSE",
                name: "M.Tech in Computer Science",
                departmentId: 1,
                durationYears: 2,
                degreeType: "PG"
            ) {
                id
                code
                name
                durationYears
            }
        }
    """
    # Non-admin blocked
    _, errors = gql(create_prog, headers=student1_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(create_prog, headers=admin_headers)
    assert errors is None
    prog_id = data["createProgram"]["id"]
    assert data["createProgram"]["code"] == "MTECH_CSE"

    # Query programs
    q_progs = "query { getPrograms { id code name } }"
    data, errors = gql(q_progs, headers=student1_headers)
    assert errors is None
    codes = [p["code"] for p in data["getPrograms"]]
    assert "MTECH_CSE" in codes

    # 2. Create Semester (Admin only)
    create_sem = f"""
        mutation {{
            createSemester(
                programId: {prog_id},
                number: 1,
                startDate: "2026-08-01",
                endDate: "2026-12-15",
                isCurrent: true
            ) {{
                id
                number
                isCurrent
            }}
        }}
    """
    _, errors = gql(create_sem, headers=student1_headers)
    assert errors is not None

    data, errors = gql(create_sem, headers=admin_headers)
    assert errors is None
    sem_id = data["createSemester"]["id"]

    # 3. Update Registration Window (Admin only)
    update_win = f"""
        mutation {{
            updateRegistrationWindow(
                semesterId: {sem_id},
                startDate: "2026-07-01",
                endDate: "2026-08-10"
            ) {{
                id
                registrationWindowStart
                registrationWindowEnd
            }}
        }}
    """
    # Student blocked
    _, errors = gql(update_win, headers=student1_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(update_win, headers=admin_headers)
    assert errors is None
    assert "2026-07-01" in data["updateRegistrationWindow"]["registrationWindowStart"]
    assert "2026-08-10" in data["updateRegistrationWindow"]["registrationWindowEnd"]

    # Invalid date format error
    bad_win = f"""
        mutation {{
            updateRegistrationWindow(
                semesterId: {sem_id},
                startDate: "bad-date",
                endDate: "2026-08-10"
            ) {{
                id
            }}
        }}
    """
    _, errors = gql(bad_win, headers=admin_headers)
    assert errors is not None
    assert "invalid date format" in errors[0]["message"].lower()

    # 4. Clean up semester and program
    data, errors = gql(f"mutation {{ deleteSemester(id: {sem_id}) }}", headers=admin_headers)
    assert errors is None and data["deleteSemester"] is True

    data, errors = gql(f"mutation {{ deleteProgram(id: {prog_id}) }}", headers=admin_headers)
    assert errors is None and data["deleteProgram"] is True

def test_batches_and_courses_crud(gql, admin_headers, student1_headers):
    # 1. Create Batch (Admin only)
    create_batch = """
        mutation {
            createBatch(
                programId: 1,
                name: "Class of 2029",
                year: 2025,
                label: "BCS-2025"
            ) {
                id
                name
                year
            }
        }
    """
    _, errors = gql(create_batch, headers=student1_headers)
    assert errors is not None

    data, errors = gql(create_batch, headers=admin_headers)
    assert errors is None
    batch_id = data["createBatch"]["id"]

    # 2. Create Course (Admin only)
    create_course = """
        mutation {
            createCourse(
                code: "CS401_TEST",
                name: "Distributed Operating Systems",
                departmentId: 1,
                credits: 4.0,
                courseType: "elective",
                description: "Advanced systems concepts"
            ) {
                id
                code
                credits
            }
        }
    """
    _, errors = gql(create_course, headers=student1_headers)
    assert errors is not None

    data, errors = gql(create_course, headers=admin_headers)
    assert errors is None
    course_id = data["createCourse"]["id"]
    assert data["createCourse"]["credits"] == 4.0

    # 3. Create Course Offering (Admin only)
    create_offering = f"""
        mutation {{
            createCourseOffering(
                courseId: {course_id},
                semesterId: 1,
                batchId: {batch_id}
            ) {{
                id
                gradeSubmissionStatus
            }}
        }}
    """
    data, errors = gql(create_offering, headers=admin_headers)
    assert errors is None
    offering_id = data["createCourseOffering"]["id"]
    assert data["createCourseOffering"]["gradeSubmissionStatus"] == "pending"

    # Allocate faculty
    alloc_fac = f"""
        mutation {{
            allocateFacultyToOffering(
                offeringId: {offering_id},
                facultyId: 1,
                role: "instructor"
            ) {{
                offeringId
                facultyId
                role
            }}
        }}
    """
    data, errors = gql(alloc_fac, headers=admin_headers)
    assert errors is None
    assert data["allocateFacultyToOffering"]["role"] == "instructor"

    # Clean up
    gql(f"mutation {{ deleteCourseOffering(id: {offering_id}) }}", headers=admin_headers)
    gql(f"mutation {{ deleteCourse(id: {course_id}) }}", headers=admin_headers)
    gql(f"mutation {{ deleteBatch(id: {batch_id}) }}", headers=admin_headers)

def test_online_semester_registration_and_subject_selection(gql, admin_headers, faculty_headers, student1_headers, student2_headers):
    # student1 is student_id 30 (user_id 3)
    # student2 is student_id 1 (user_id 12)
    # Semester 1 is active

    # 1. Student1 registers for Semester 1 (Self) -> Allowed
    reg_self = """
        mutation {
            registerForSemester(studentId: 30, semesterId: 1) {
                id
                studentId
                semesterId
                status
                totalCredits
            }
        }
    """
    data, errors = gql(reg_self, headers=student1_headers)
    assert errors is None
    reg_id = data["registerForSemester"]["id"]
    assert data["registerForSemester"]["studentId"] == 30

    # 2. Student1 attempts to register Student2 -> BLOCKED (Strict Privacy / Access Control)
    reg_other = """
        mutation {
            registerForSemester(studentId: 1, semesterId: 1) {
                id
            }
        }
    """
    data, errors = gql(reg_other, headers=student1_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

    # 3. Idempotent registration: Student1 registering again returns existing registration
    data, errors = gql(reg_self, headers=student1_headers)
    assert errors is None
    assert data["registerForSemester"]["id"] == reg_id

    # 4. Student1 queries their registration
    q_reg = f"query {{ getSemesterRegistration(id: {reg_id}) {{ id status studentId }} }}"
    data, errors = gql(q_reg, headers=student1_headers)
    assert errors is None
    assert data["getSemesterRegistration"]["id"] == reg_id

    # Student2 queries Student1's registration -> BLOCKED
    data, errors = gql(q_reg, headers=student2_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

    # Faculty & Admin queries Student1's registration -> ALLOWED
    data, errors = gql(q_reg, headers=faculty_headers)
    assert errors is None
    data, errors = gql(q_reg, headers=admin_headers)
    assert errors is None

    # 5. getMySemesterRegistrations
    q_my_regs = "query { getMySemesterRegistrations { id studentId semesterId } }"
    data, errors = gql(q_my_regs, headers=student1_headers)
    assert errors is None
    assert any(r["id"] == reg_id for r in data["getMySemesterRegistrations"])

    # 6. Online Subject Selection (including Backlog courses)
    # Offering 1 is EE101 (4.0 credits)
    select_sub = f"""
        mutation {{
            selectSubject(
                registrationId: {reg_id},
                courseOfferingId: 1,
                isBacklog: true
            ) {{
                id
                courseOfferingId
                isBacklog
            }}
        }}
    """
    # Student2 cannot select subjects for Student1's registration
    _, errors = gql(select_sub, headers=student2_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

    # Student1 can select subjects
    data, errors = gql(select_sub, headers=student1_headers)
    assert errors is None
    assert data["selectSubject"]["isBacklog"] is True

    # 7. Query subject registrations
    q_subs = f"query {{ getSubjectRegistrations(registrationId: {reg_id}) {{ id courseOfferingId isBacklog }} }}"
    data, errors = gql(q_subs, headers=student1_headers)
    assert errors is None
    assert len(data["getSubjectRegistrations"]) > 0

    # Student2 blocked from viewing Student1's subject registrations
    _, errors = gql(q_subs, headers=student2_headers)
    assert errors is not None

    # 8. Admin updates registration status (approves and clears fees)
    update_status = f"""
        mutation {{
            updateSemesterRegistrationStatus(
                registrationId: {reg_id},
                status: "approved",
                instituteFeePaid: true,
                hostelFeePaid: true
            ) {{
                id
                status
                instituteFeePaid
                hostelFeePaid
            }}
        }}
    """
    # Student blocked
    _, errors = gql(update_status, headers=student1_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(update_status, headers=admin_headers)
    assert errors is None
    assert data["updateSemesterRegistrationStatus"]["status"] == "approved"
    assert data["updateSemesterRegistrationStatus"]["instituteFeePaid"] is True
