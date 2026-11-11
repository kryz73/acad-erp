import pytest

def test_assessment_components_crud_and_rbac(gql, admin_headers, faculty_headers, student1_headers):
    # 1. Create Assessment Component (Faculty allowed, Student blocked)
    create_comp = """
        mutation {
            createAssessmentComponent(
                offeringId: 1,
                name: "Mini Project",
                maxMarks: 50.0,
                weightagePct: 20.0,
                conductedOn: "2026-10-15"
            ) {
                id
                offeringId
                name
                maxMarks
                weightagePct
            }
        }
    """
    # Student blocked
    _, errors = gql(create_comp, headers=student1_headers)
    assert errors is not None

    # Faculty allowed
    data, errors = gql(create_comp, headers=faculty_headers)
    assert errors is None
    comp_id = data["createAssessmentComponent"]["id"]
    assert data["createAssessmentComponent"]["name"] == "Mini Project"

    # 2. Query components
    q_comps = "query { getAssessmentComponents(offeringId: 1) { id name maxMarks } }"
    data, errors = gql(q_comps, headers=student1_headers)
    assert errors is None
    assert any(c["id"] == comp_id for c in data["getAssessmentComponents"])

    # 3. Delete component (Admin only)
    del_comp = f"mutation {{ deleteAssessmentComponent(id: {comp_id}) }}"
    # Student & Faculty blocked from deleting component
    _, errors = gql(del_comp, headers=student1_headers)
    assert errors is not None
    _, errors = gql(del_comp, headers=faculty_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(del_comp, headers=admin_headers)
    assert errors is None
    assert data["deleteAssessmentComponent"] is True

def test_student_marks_recording_and_privacy(gql, admin_headers, faculty_headers, student1_headers, student2_headers):
    # Student 1 is student_id 30 (user_id 3)
    # Student 2 is student_id 1 (user_id 12)
    # Component 1 exists on offering 1

    # 1. Faculty records marks for Student 1
    rec_marks = """
        mutation {
            recordStudentMarks(
                componentId: 1,
                studentId: 30,
                marksObtained: 18.5,
                isAbsent: false
            ) {
                id
                componentId
                studentId
                marksObtained
                isAbsent
            }
        }
    """
    # Student blocked from recording marks
    _, errors = gql(rec_marks, headers=student1_headers)
    assert errors is not None

    # Faculty allowed
    data, errors = gql(rec_marks, headers=faculty_headers)
    assert errors is None
    assert data["recordStudentMarks"]["marksObtained"] == 18.5

    # 2. Student 1 queries own marks -> ALLOWED
    q_marks_self = "query { getStudentMarks(studentId: 30) { id componentId marksObtained } }"
    data, errors = gql(q_marks_self, headers=student1_headers)
    assert errors is None
    assert len(data["getStudentMarks"]) > 0

    # 3. Student 1 queries Student 2's marks -> BLOCKED (Strict Privacy Rule!)
    q_marks_other = "query { getStudentMarks(studentId: 1) { id componentId marksObtained } }"
    data, errors = gql(q_marks_other, headers=student1_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

    # 4. Faculty and Admin can query both
    data, errors = gql(q_marks_self, headers=faculty_headers)
    assert errors is None
    data, errors = gql(q_marks_other, headers=faculty_headers)
    assert errors is None
    data, errors = gql(q_marks_self, headers=admin_headers)
    assert errors is None

def test_component_statistics_analytics(gql, student1_headers, faculty_headers):
    # Component statistics: returns class average, median, min, max without exposing individual student grades
    q_stats = "query { getComponentStatistics(componentId: 1) { componentId average median highest lowest totalStudents } }"
    data, errors = gql(q_stats, headers=student1_headers)
    assert errors is None
    stats = data["getComponentStatistics"]
    assert stats is not None
    assert stats["componentId"] == 1
    assert stats["totalStudents"] > 0
    assert stats["highest"] >= stats["lowest"]
    assert stats["average"] > 0

def test_grade_rules_and_scale(gql, admin_headers, student1_headers):
    # 1. Query grade rules
    q_rules = "query { getGradeRules(programId: 1) { id programId gradeLetter minPercentage maxPercentage gradePoint } }"
    data, errors = gql(q_rules, headers=student1_headers)
    assert errors is None
    letters = [r["gradeLetter"] for r in data["getGradeRules"]]
    assert "O" in letters
    assert "A+" in letters
    assert "F" in letters

    # 2. Create grade rule (Admin only)
    create_rule = """
        mutation {
            createGradeRule(
                programId: 1,
                gradeLetter: "A++",
                minPercentage: 95.0,
                maxPercentage: 100.0,
                gradePoint: 10.0
            ) {
                id
                gradeLetter
            }
        }
    """
    _, errors = gql(create_rule, headers=student1_headers)
    assert errors is not None

    data, errors = gql(create_rule, headers=admin_headers)
    assert errors is None
    rule_id = data["createGradeRule"]["id"]

    # Delete grade rule
    del_rule = f"mutation {{ deleteGradeRule(id: {rule_id}) }}"
    data, errors = gql(del_rule, headers=admin_headers)
    assert errors is None and data["deleteGradeRule"] is True

def test_grade_workflow_locking_and_approval(gql, admin_headers, faculty_headers, student1_headers, student2_headers):
    # Offering 2
    # 1. Faculty stores grades for offering 2
    calc_grade = """
        mutation {
            calculateAndStoreGrades(
                offeringId: 2,
                studentId: 30,
                totalMarks: 88.0,
                gradeLetter: "A+",
                gradePoint: 9.0
            ) {
                id
                offeringId
                studentId
                gradeLetter
                isPublished
            }
        }
    """
    # Student blocked
    _, errors = gql(calc_grade, headers=student1_headers)
    assert errors is not None

    # Faculty stores grade (starts unpublished)
    data, errors = gql(calc_grade, headers=faculty_headers)
    assert errors is None
    assert data["calculateAndStoreGrades"]["isPublished"] is False

    # 2. Student 1 queries unpublished grade -> cannot see unpublished grade
    q_offering_grades = "query { getOfferingGrades(offeringId: 2) { id studentId gradeLetter isPublished } }"
    data, errors = gql(q_offering_grades, headers=student1_headers)
    assert errors is None
    assert len(data["getOfferingGrades"]) == 0

    # 3. Faculty submits grades for review
    submit_m = "mutation { submitGrades(offeringId: 2) }"
    # Student blocked from submitting grades
    _, errors = gql(submit_m, headers=student1_headers)
    assert errors is not None

    data, errors = gql(submit_m, headers=faculty_headers)
    assert errors is None
    assert data["submitGrades"] is True

    # 4. Modifying marks or grades after submission is LOCKED
    _, errors = gql(calc_grade, headers=faculty_headers)
    assert errors is not None
    assert "cannot modify" in errors[0]["message"].lower()

    # 5. Admin reviews and approves grades (Publishing them officially!)
    review_m = """
        mutation {
            reviewGrades(offeringId: 2, action: "approve")
        }
    """
    # Faculty blocked from reviewing grades (Admin only)
    _, errors = gql(review_m, headers=faculty_headers)
    assert errors is not None

    # Admin approves
    data, errors = gql(review_m, headers=admin_headers)
    assert errors is None
    assert data["reviewGrades"] is True

    # 6. Student 1 now queries published grade -> Allowed, sees own grade
    data, errors = gql(q_offering_grades, headers=student1_headers)
    assert errors is None
    assert len(data["getOfferingGrades"]) == 1
    assert data["getOfferingGrades"][0]["studentId"] == 30
    assert data["getOfferingGrades"][0]["isPublished"] is True

    # Student 2 queries offering 2 -> cannot see Student 1's grade
    data, errors = gql(q_offering_grades, headers=student2_headers)
    assert errors is None
    assert not any(g["studentId"] == 30 for g in data["getOfferingGrades"])

def test_student_semester_result_sgpa_cgpa(gql, admin_headers, student1_headers, student2_headers):
    # Student 1 is id 30, Semester 1
    q_res_self = "query { getStudentSemesterResult(studentId: 30, semesterId: 1) { id sgpa cgpa totalCreditsEarned } }"
    data, errors = gql(q_res_self, headers=student1_headers)
    assert errors is None
    assert data["getStudentSemesterResult"]["sgpa"] == 8.8
    assert data["getStudentSemesterResult"]["cgpa"] == 8.5

    # Student 1 queries Student 2's results -> BLOCKED
    q_res_other = "query { getStudentSemesterResult(studentId: 1, semesterId: 1) { id sgpa cgpa } }"
    data, errors = gql(q_res_other, headers=student1_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

    # Admin queries Student 2's results -> Allowed
    data, errors = gql(q_res_other, headers=admin_headers)
    assert errors is None
    assert data["getStudentSemesterResult"]["sgpa"] is not None
