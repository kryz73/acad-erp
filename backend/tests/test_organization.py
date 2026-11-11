import pytest

def test_departments_crud_and_rbac(gql, admin_headers, faculty_headers, student1_headers):
    # 1. Create department (Admin only)
    create_mutation = """
        mutation {
            createDepartment(code: "AI_DS", name: "Artificial Intelligence and Data Science") {
                id
                code
                name
            }
        }
    """
    # Student blocked
    _, errors = gql(create_mutation, headers=student1_headers)
    assert errors is not None

    # Faculty blocked
    _, errors = gql(create_mutation, headers=faculty_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(create_mutation, headers=admin_headers)
    assert errors is None
    dept_id = data["createDepartment"]["id"]
    assert data["createDepartment"]["code"] == "AI_DS"

    # 2. Query department & departments (All authenticated allowed)
    query_one = f"query {{ getDepartment(departmentId: {dept_id}) {{ id code name }} }}"
    data, errors = gql(query_one, headers=student1_headers)
    assert errors is None
    assert data["getDepartment"]["code"] == "AI_DS"

    query_all = "query { getDepartments { id code name } }"
    data, errors = gql(query_all, headers=student1_headers)
    assert errors is None
    codes = [d["code"] for d in data["getDepartments"]]
    assert "AI_DS" in codes
    assert "CSE" in codes

    # 3. Delete department (Admin only)
    delete_mutation = f"mutation {{ deleteDepartment(id: {dept_id}) }}"
    # Student blocked
    _, errors = gql(delete_mutation, headers=student1_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(delete_mutation, headers=admin_headers)
    assert errors is None
    assert data["deleteDepartment"] is True

def test_faculty_profiles(gql, admin_headers, faculty_headers, student1_headers):
    # 1. Query faculty profiles (All authenticated allowed)
    query_all = "query { getFacultyProfiles { id employeeId firstName lastName title } }"
    data, errors = gql(query_all, headers=student1_headers)
    assert errors is None
    assert len(data["getFacultyProfiles"]) > 0

    # 2. Get my faculty profile
    query_my_fac = "query { getMyFacultyProfile { id employeeId firstName } }"
    # Faculty calling getMyFacultyProfile
    data, errors = gql(query_my_fac, headers=faculty_headers)
    assert errors is None
    assert data["getMyFacultyProfile"] is not None

    # Student calling getMyFacultyProfile returns null
    data, errors = gql(query_my_fac, headers=student1_headers)
    assert errors is None
    assert data["getMyFacultyProfile"] is None

    # 3. Create faculty profile (Admin only)
    # First create a user for faculty
    create_user_mutation = """
        mutation {
            createUser(email: "prof_new@college.edu", password: "password123") {
                id
            }
        }
    """
    u_data, _ = gql(create_user_mutation)
    new_u_id = u_data["createUser"]["id"]

    create_fac_mutation = f"""
        mutation {{
            createFacultyProfile(
                userId: {new_u_id},
                employeeId: "FAC_NEW_99",
                firstName: "Alan",
                lastName: "Turing",
                departmentId: 1,
                title: "Chair Professor"
            ) {{
                id
                employeeId
                firstName
                title
            }}
        }}
    """
    # Student blocked
    _, errors = gql(create_fac_mutation, headers=student1_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(create_fac_mutation, headers=admin_headers)
    assert errors is None
    assert data["createFacultyProfile"]["employeeId"] == "FAC_NEW_99"

def test_student_profiles_privacy_and_access_control(gql, admin_headers, faculty_headers, student1_headers, student2_headers):
    # student1 is student_id 30 (user_id 3, roll: 26BCS001)
    # student2 is student_id 1 (user_id 12, roll: 2024BMS-001)

    # 1. Student1 queries own profile (id: 30) -> Allowed
    query_self = "query { getStudentProfile(profileId: 30) { id rollNumber firstName targetCgpa } }"
    data, errors = gql(query_self, headers=student1_headers)
    assert errors is None
    assert data["getStudentProfile"]["id"] == 30
    assert data["getStudentProfile"]["rollNumber"] == "26BCS001"

    # 2. Student1 queries Student2 profile (id: 1) -> BLOCKED (Strict Privacy Constraint!)
    query_other = "query { getStudentProfile(profileId: 1) { id rollNumber firstName } }"
    data, errors = gql(query_other, headers=student1_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

    # 3. Student2 queries own profile (id: 1) -> Allowed
    data, errors = gql(query_other, headers=student2_headers)
    assert errors is None
    assert data["getStudentProfile"]["id"] == 1
    assert data["getStudentProfile"]["rollNumber"] == "2024BMS-001"

    # 4. Faculty queries Student1 profile (id: 30) -> Allowed
    data, errors = gql(query_self, headers=faculty_headers)
    assert errors is None
    assert data["getStudentProfile"]["id"] == 30

    # 5. Admin queries Student2 profile (id: 1) -> Allowed
    data, errors = gql(query_other, headers=admin_headers)
    assert errors is None
    assert data["getStudentProfile"]["id"] == 1

    # 6. getMyStudentProfile
    query_my = "query { getMyStudentProfile { id rollNumber firstName targetCgpa } }"
    data, errors = gql(query_my, headers=student1_headers)
    assert errors is None
    assert data["getMyStudentProfile"]["rollNumber"] == "26BCS001"

    data2, errors2 = gql(query_my, headers=student2_headers)
    assert errors2 is None
    assert data2["getMyStudentProfile"]["rollNumber"] == "2024BMS-001"

    # 7. getStudentProfiles (List all students)
    query_all_students = "query { getStudentProfiles { id rollNumber } }"
    # Student CANNOT view all students
    data, errors = gql(query_all_students, headers=student1_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

    # Faculty CAN view all students
    data, errors = gql(query_all_students, headers=faculty_headers)
    assert errors is None
    assert len(data["getStudentProfiles"]) > 1

    # Admin CAN view all students
    data, errors = gql(query_all_students, headers=admin_headers)
    assert errors is None
    assert len(data["getStudentProfiles"]) > 1

def test_target_cgpa_goal_tracking(gql, admin_headers, student1_headers, student2_headers):
    # Goal Tracking System: Student inputs a Target CGPA
    # 1. Student1 updates own target CGPA
    update_self = """
        mutation {
            updateStudentTargetCgpa(studentId: 30, targetCgpa: 9.25) {
                id
                targetCgpa
            }
        }
    """
    data, errors = gql(update_self, headers=student1_headers)
    assert errors is None
    assert data["updateStudentTargetCgpa"]["targetCgpa"] == 9.25

    # 2. Student1 attempts to update Student2's target CGPA -> BLOCKED
    update_other = """
        mutation {
            updateStudentTargetCgpa(studentId: 1, targetCgpa: 5.0) {
                id
            }
        }
    """
    data, errors = gql(update_other, headers=student1_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

    # 3. Admin updates Student2's target CGPA -> Allowed
    update_admin = """
        mutation {
            updateStudentTargetCgpa(studentId: 1, targetCgpa: 8.75) {
                id
                targetCgpa
            }
        }
    """
    data, errors = gql(update_admin, headers=admin_headers)
    assert errors is None
    assert data["updateStudentTargetCgpa"]["targetCgpa"] == 8.75
