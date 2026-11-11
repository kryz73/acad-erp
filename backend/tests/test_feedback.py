import pytest

def test_course_feedback_links_crud_and_contextual_access(gql, admin_headers, faculty_headers, student1_headers):
    # 1. Create Course Feedback Link (Faculty allowed, Student blocked)
    create_link = """
        mutation {
            createCourseFeedbackLink(
                offeringId: 1,
                facultyId: 1,
                formUrl: "https://forms.gle/testFeedbackForm123",
                isActive: true
            ) {
                id
                offeringId
                facultyId
                formUrl
                isActive
            }
        }
    """
    # Student blocked
    _, errors = gql(create_link, headers=student1_headers)
    assert errors is not None

    # Faculty allowed
    data, errors = gql(create_link, headers=faculty_headers)
    assert errors is None
    link_id = data["createCourseFeedbackLink"]["id"]
    assert data["createCourseFeedbackLink"]["formUrl"] == "https://forms.gle/testFeedbackForm123"

    # 2. Contextual Access: Student 1 is actively enrolled in offering 1
    q_links = "query { getCourseFeedbackLinks(offeringId: 1) { id formUrl isActive } }"
    data, errors = gql(q_links, headers=student1_headers)
    assert errors is None
    assert any(l["id"] == link_id for l in data["getCourseFeedbackLinks"])

    # Faculty & Admin can query feedback links
    data, errors = gql(q_links, headers=faculty_headers)
    assert errors is None
    assert any(l["id"] == link_id for l in data["getCourseFeedbackLinks"])

    data, errors = gql(q_links, headers=admin_headers)
    assert errors is None
    assert any(l["id"] == link_id for l in data["getCourseFeedbackLinks"])

    # 3. Delete Feedback Link (Faculty/Admin allowed, Student blocked)
    del_link = f"mutation {{ deleteCourseFeedbackLink(id: {link_id}) }}"
    _, errors = gql(del_link, headers=student1_headers)
    assert errors is not None

    data, errors = gql(del_link, headers=faculty_headers)
    assert errors is None
    assert data["deleteCourseFeedbackLink"] is True
