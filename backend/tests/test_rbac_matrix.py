import pytest
import uuid

def test_rbac_queries_matrix(gql, admin_headers, faculty_headers, student1_headers):
    # Matrix of (Query Name, Query String, Expected Status for [Admin, Faculty, Student, Unauth])
    # Status: True for ALLOWED, False for BLOCKED
    # Student1 is student_id: 30, user_id: 3
    # Student2 is student_id: 1, user_id: 12
    test_cases = [
        (
            "getUsers (Admin Only)",
            "query { getUsers { id email } }",
            [True, False, False, False]
        ),
        (
            "getDepartments (All Authenticated)",
            "query { getDepartments { id name } }",
            [True, True, True, False]
        ),
        (
            "getStudentProfiles (Elevated Only)",
            "query { getStudentProfiles { id firstName } }",
            [True, True, False, False]
        ),
        (
            "getPrograms (All Authenticated)",
            "query { getPrograms { id name } }",
            [True, True, True, False]
        ),
        (
            "getRooms (All Authenticated)",
            "query { getRooms { id code } }",
            [True, True, True, False]
        ),
        (
            "getStudentMarks (Self: Student 1 queries Student 1)",
            "query { getStudentMarks(studentId: 30) { id marksObtained } }",
            [True, True, True, False]
        ),
        (
            "getStudentMarks (Cross: Student 1 queries Student 2)",
            "query { getStudentMarks(studentId: 1) { id marksObtained } }",
            [True, True, False, False]
        ),
        (
            "getStudentFeeStatus (Self: Student 1 queries Student 1)",
            "query { getStudentFeeStatus(studentId: 30) { id status } }",
            [True, True, True, False]
        ),
        (
            "getStudentFeeStatus (Cross: Student 1 queries Student 2)",
            "query { getStudentFeeStatus(studentId: 1) { id status } }",
            [True, True, False, False]
        ),
        (
            "getAllFees (Admin Only)",
            "query { getAllFees { id status } }",
            [True, False, False, False]
        )
    ]

    actors = [
        ("Admin", admin_headers),
        ("Faculty", faculty_headers),
        ("Student", student1_headers),
        ("Unauth", None),
    ]

    for name, query, expected_results in test_cases:
        for idx, (actor_name, headers) in enumerate(actors):
            data, errors = gql(query, headers=headers)
            is_allowed = errors is None and data is not None
            expected = expected_results[idx]
            assert is_allowed == expected, (
                f"RBAC Matrix Failure for '{name}' with actor '{actor_name}': "
                f"expected allowed={expected}, but got allowed={is_allowed} (errors={errors})"
            )

def test_rbac_mutations_matrix(gql, admin_headers, faculty_headers, student1_headers):
    # Student1 is user_id: 3, student_id: 30
    
    # 1. createProgram (Admin only)
    code = f"PROG_{uuid.uuid4().hex[:6].upper()}"
    create_prog = f"""
        mutation {{
            createProgram(
                code: "{code}",
                name: "Test Prog {code}",
                departmentId: 1,
                durationYears: 4,
                degreeType: "UG"
            ) {{ id }}
        }}
    """
    # Unauth -> Blocked
    _, errors = gql(create_prog)
    assert errors is not None
    # Student -> Blocked
    _, errors = gql(create_prog, headers=student1_headers)
    assert errors is not None
    # Faculty -> Blocked
    _, errors = gql(create_prog, headers=faculty_headers)
    assert errors is not None
    # Admin -> Allowed
    data, errors = gql(create_prog, headers=admin_headers)
    assert errors is None
    prog_id = data["createProgram"]["id"]
    # Cleanup
    gql(f"mutation {{ deleteProgram(id: {prog_id}) }}", headers=admin_headers)

    # 2. recordStudentMarks (Faculty & Admin allowed, Student & Unauth blocked)
    rec_marks = """
        mutation {
            recordStudentMarks(
                componentId: 1,
                studentId: 30,
                marksObtained: 19.0,
                isAbsent: false
            ) { id marksObtained }
        }
    """
    # Unauth -> Blocked
    _, errors = gql(rec_marks)
    assert errors is not None
    # Student -> Blocked
    _, errors = gql(rec_marks, headers=student1_headers)
    assert errors is not None
    # Faculty -> Allowed
    data, errors = gql(rec_marks, headers=faculty_headers)
    assert errors is None
    # Admin -> Allowed
    data, errors = gql(rec_marks, headers=admin_headers)
    assert errors is None

    # 3. registerForSemester (Self: Student 1 registers Student 1)
    # Student & Admin allowed; Faculty & Unauth blocked
    reg_self = """
        mutation {
            registerForSemester(studentId: 30, semesterId: 1) { id status }
        }
    """
    # Unauth -> Blocked
    _, errors = gql(reg_self)
    assert errors is not None
    # Faculty -> Blocked (Faculty does not have Student role)
    _, errors = gql(reg_self, headers=faculty_headers)
    assert errors is not None
    # Student -> Allowed
    data, errors = gql(reg_self, headers=student1_headers)
    assert errors is None
    # Admin -> Allowed (Admin has all roles)
    data, errors = gql(reg_self, headers=admin_headers)
    assert errors is None

    # 4. updateUser (Self: Student 1 updates user 3)
    upd_self = """
        mutation {
            updateUser(userId: 3, isActive: true) { id }
        }
    """
    # Unauth -> Blocked
    _, errors = gql(upd_self)
    assert errors is not None
    # Student -> Allowed (Self)
    data, errors = gql(upd_self, headers=student1_headers)
    assert errors is None
    # Admin -> Allowed
    data, errors = gql(upd_self, headers=admin_headers)
    assert errors is None

    # 5. updateUser (Cross: Student 1 updates user 1)
    upd_cross = """
        mutation {
            updateUser(userId: 1, isActive: true) { id }
        }
    """
    # Student -> Blocked (Cannot update another user)
    _, errors = gql(upd_cross, headers=student1_headers)
    assert errors is not None
    # Faculty -> Blocked (Cannot update another user)
    _, errors = gql(upd_cross, headers=faculty_headers)
    assert errors is not None
