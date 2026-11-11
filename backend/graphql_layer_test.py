import json
import logging
import random
import string
from fastapi.testclient import TestClient
from main import app

# Suppress backend error logs from bleeding into the console matrix
logging.disable(logging.CRITICAL)

client = TestClient(app)

USERS = {
    "Admin": ("admin@college.edu", "password123"),
    "Faculty": ("faculty@college.edu", "password123"),
    "Student": ("student@college.edu", "password123"),
    "Unauth": (None, None)
}

def get_random_string(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

QUERIES = {
    "getUsers": "query { getUsers { id email } }",
    "getDepartments": "query { getDepartments { id name } }",
    "getStudentProfiles": "query { getStudentProfiles { id firstName } }",
    "getStudentProfile (Self)": "query { getStudentProfile(profileId: 30) { id firstName } }",
    "getPrograms": "query { getPrograms { id name } }",
    "getSemesterReg (Self)": "query { getSemesterRegistration(id: 30) { id status } }",
    "getRooms": "query { getRooms { id code } }",
    "getStudentMarks (Self)": "query { getStudentMarks(studentId: 30) { id marksObtained } }",
    "getExamResults (Self)": "query { getExamResults(examScheduleId: 1) { id marksObtained } }",
    "getStudentFeeStatus (Self)": "query { getStudentFeeStatus(studentId: 30) { id status } }",
}

MUTATIONS = {
    "createProgram (Admin Only)": """
        mutation {
            createProgram(
                code: "PROG_RAND",
                name: "Random Program RAND",
                departmentId: 1,
                durationYears: 4,
                degreeType: "UG"
            ) { id }
        }
    """,
    "recordStudentMarks (Faculty Only)": """
        mutation {
            recordStudentMarks(
                componentId: 1,
                studentId: 30,
                marksObtained: 95.5,
                isAbsent: false
            ) { id }
        }
    """,
    "registerForSemester (Student Self)": """
        mutation {
            registerForSemester(
                studentId: 30,
                semesterId: 1
            ) { id }
        }
    """,
    "updateUser (Self)": """
        mutation {
            updateUser(
                userId: 3,
                isActive: true
            ) { id }
        }
    """
}

# Mapping of mutation keys to cleanup mutations
CLEANUP = {
    "createProgram (Admin Only)": "mutation { deleteProgram(id: ID_PLACEHOLDER) }",
    # recordStudentMarks and registerForSemester are updates/idempotent or hard to delete without cascaded effects, 
    # but we will try to keep the database state stable.
}

def get_token(username, password):
    if not username:
        return None
    res = client.post("/auth/token", data={"username": username, "password": password})
    if res.status_code == 200:
        return res.json()["access_token"]
    return None

def run_test_suite():
    tokens = {}
    for user_type, (email, pwd) in USERS.items():
        tokens[user_type] = get_token(email, pwd)

    print(f"\n{'Operation Name':<35} | {'Admin':<10} | {'Faculty':<10} | {'Student':<10} | {'Unauth':<10}")
    print("-" * 85)

    # 1. Test Queries
    for name, q_string in QUERIES.items():
        row = execute_and_format(name, q_string, tokens)
        print(row)

    print("\n" + "-" * 85)
    
    # 2. Test Mutations
    created_ids = {} # Store IDs for cleanup

    for name, m_string in MUTATIONS.items():
        # Randomize content to avoid collisions
        rand = get_random_string()
        current_m = m_string.replace("RAND", rand)
        
        row, first_id = execute_and_format_mutation(name, current_m, tokens)
        print(row)
        if first_id:
            created_ids[name] = first_id

    # 3. Cleanup
    admin_token = tokens["Admin"]
    if admin_token:
        headers = {"Authorization": f"Bearer {admin_token}"}
        for name, id_val in created_ids.items():
            if name in CLEANUP:
                cleanup_q = CLEANUP[name].replace("ID_PLACEHOLDER", str(id_val))
                client.post("/graphql", json={"query": cleanup_q}, headers=headers)

def execute_and_format(name, query, tokens):
    results = []
    for user_type in ["Admin", "Faculty", "Student", "Unauth"]:
        token = tokens[user_type]
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        res = client.post("/graphql", json={"query": query}, headers=headers)
        
        status = "ERROR"
        if res.status_code == 200:
            body = res.json()
            if "errors" in body:
                status = "BLOCKED"
            elif "data" in body:
                status = "ALLOWED"
        else:
            status = f"E{res.status_code}"
        results.append(status)
    return f"{name:<35} | {results[0]:<10} | {results[1]:<10} | {results[2]:<10} | {results[3]:<10}"

def execute_and_format_mutation(name, mutation, tokens):
    results = []
    first_id = None
    for user_type in ["Admin", "Faculty", "Student", "Unauth"]:
        token = tokens[user_type]
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        res = client.post("/graphql", json={"query": mutation}, headers=headers)
        
        status = "ERROR"
        if res.status_code == 200:
            body = res.json()
            if "errors" in body:
                status = "BLOCKED"
            elif "data" in body:
                status = "ALLOWED"
                # Capture ID from Admin or Faculty success for cleanup
                if user_type in ["Admin", "Faculty"] and not first_id:
                    data = body["data"]
                    for val in data.values():
                        if val and "id" in val:
                            first_id = val["id"]
        else:
            status = f"E{res.status_code}"
        results.append(status)
    return f"{name:<35} | {results[0]:<10} | {results[1]:<10} | {results[2]:<10} | {results[3]:<10}", first_id

if __name__ == "__main__":
    run_test_suite()
