import pytest

def test_get_me_for_all_roles(gql, admin_headers, faculty_headers, student1_headers):
    query = "query { getMe { id email roles } }"
    
    # 1. Admin
    data, errors = gql(query, headers=admin_headers)
    assert errors is None
    assert data["getMe"]["email"] == "admin@college.edu"
    assert "Admin" in data["getMe"]["roles"]

    # 2. Faculty
    data, errors = gql(query, headers=faculty_headers)
    assert errors is None
    assert data["getMe"]["email"] == "faculty@college.edu"
    assert "Faculty" in data["getMe"]["roles"]

    # 3. Student
    data, errors = gql(query, headers=student1_headers)
    assert errors is None
    assert data["getMe"]["email"] == "student@college.edu"
    assert "Student" in data["getMe"]["roles"]

def test_get_user_self_and_ownership(gql, admin_headers, student1_headers, student2_headers):
    # Student1 is user_id 3, Student2 is user_id 12, Admin is user_id 1
    
    # 1. Student1 queries own record (user_id: 3) -> Allowed
    query_self = "query { getUser(userId: 3) { id email isActive } }"
    data, errors = gql(query_self, headers=student1_headers)
    assert errors is None
    assert data["getUser"]["id"] == 3
    assert data["getUser"]["email"] == "student@college.edu"

    # 2. Admin queries Student1 record (user_id: 3) -> Allowed
    data, errors = gql(query_self, headers=admin_headers)
    assert errors is None
    assert data["getUser"]["id"] == 3

    # 3. Student1 queries Admin (user_id: 1) -> Blocked (Unauthorized)
    query_admin = "query { getUser(userId: 1) { id email } }"
    data, errors = gql(query_admin, headers=student1_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

    # 4. Student1 queries Student2 (user_id: 12) -> Blocked (Unauthorized)
    query_student2 = "query { getUser(userId: 12) { id email } }"
    data, errors = gql(query_student2, headers=student1_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

def test_get_users_admin_only(gql, admin_headers, faculty_headers, student1_headers):
    query = "query { getUsers { id email } }"
    
    # Admin allowed
    data, errors = gql(query, headers=admin_headers)
    assert errors is None
    assert len(data["getUsers"]) > 0

    # Faculty blocked
    data, errors = gql(query, headers=faculty_headers)
    assert errors is not None

    # Student blocked
    data, errors = gql(query, headers=student1_headers)
    assert errors is not None

    # Unauthenticated blocked
    data, errors = gql(query)
    assert errors is not None

def test_roles_queries_and_mutations(gql, admin_headers, faculty_headers, student1_headers):
    # 1. Get roles (Admin only)
    query_roles = "query { getRoles { id name description } }"
    data, errors = gql(query_roles, headers=admin_headers)
    assert errors is None
    role_names = [r["name"] for r in data["getRoles"]]
    assert "Admin" in role_names
    assert "Faculty" in role_names
    assert "Student" in role_names

    # Non-admin blocked from getRoles
    _, errors = gql(query_roles, headers=student1_headers)
    assert errors is not None

    # 2. Create role (Admin only)
    create_role_mutation = """
        mutation {
            createRole(name: "Dean", description: "Academic Dean") {
                id
                name
            }
        }
    """
    # Non-admin blocked
    _, errors = gql(create_role_mutation, headers=faculty_headers)
    assert errors is not None

    # Admin creates role
    data, errors = gql(create_role_mutation, headers=admin_headers)
    assert errors is None
    dean_role_id = data["createRole"]["id"]
    assert data["createRole"]["name"] == "Dean"

    # Duplicate role creation raises error
    _, errors = gql(create_role_mutation, headers=admin_headers)
    assert errors is not None
    assert "already exists" in errors[0]["message"]

    # 3. Assign role to user (Admin only)
    assign_mutation = f"""
        mutation {{
            assignRoleToUser(userId: 2, roleId: {dean_role_id})
        }}
    """
    # Student blocked
    _, errors = gql(assign_mutation, headers=student1_headers)
    assert errors is not None

    # Admin succeeds
    data, errors = gql(assign_mutation, headers=admin_headers)
    assert errors is None
    assert data["assignRoleToUser"] is True

def test_create_and_update_user_graphql(gql, admin_headers, student1_headers):
    # 1. Create user via GraphQL mutation
    create_user_mutation = """
        mutation {
            createUser(email: "gql_test_user@college.edu", password: "SecretPassword123") {
                id
                email
                isActive
            }
        }
    """
    data, errors = gql(create_user_mutation)
    assert errors is None
    new_user_id = data["createUser"]["id"]
    assert data["createUser"]["email"] == "gql_test_user@college.edu"

    # Duplicate creation error
    _, errors = gql(create_user_mutation)
    assert errors is not None
    assert "already exists" in errors[0]["message"]

    # 2. Update user self
    update_self = """
        mutation {
            updateUser(userId: 3, isActive: true) {
                id
                isActive
            }
        }
    """
    data, errors = gql(update_self, headers=student1_headers)
    assert errors is None
    assert data["updateUser"]["id"] == 3

    # 3. Student tries to update another user -> Blocked
    update_other = f"""
        mutation {{
            updateUser(userId: {new_user_id}, isActive: false) {{
                id
            }}
        }}
    """
    data, errors = gql(update_other, headers=student1_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

    # 4. Admin updates another user -> Allowed
    data, errors = gql(update_other, headers=admin_headers)
    assert errors is None
    assert data["updateUser"]["id"] == new_user_id
