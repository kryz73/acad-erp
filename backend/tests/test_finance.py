import pytest

def test_student_fee_status_and_privacy(gql, admin_headers, faculty_headers, student1_headers, student2_headers):
    # Student 1 is student_id 30 (user_id 3)
    # Student 2 is student_id 1 (user_id 12)

    # 1. Student 1 queries own fee status -> Allowed
    q_fee_self = "query { getStudentFeeStatus(studentId: 30) { id studentId amount status } }"
    data, errors = gql(q_fee_self, headers=student1_headers)
    assert errors is None
    assert len(data["getStudentFeeStatus"]) > 0

    # 2. Student 1 queries Student 2's fee status -> BLOCKED (Strict Privacy Constraint!)
    q_fee_other = "query { getStudentFeeStatus(studentId: 1) { id studentId amount status } }"
    data, errors = gql(q_fee_other, headers=student1_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

    # 3. Admin can query any student's fee status
    data, errors = gql(q_fee_other, headers=admin_headers)
    assert errors is None
    assert len(data["getStudentFeeStatus"]) > 0

def test_fee_receipts_privacy(gql, admin_headers, student1_headers, student2_headers):
    # 1. Student 1 queries own fee receipts -> Allowed
    q_receipts_self = "query { getFeeReceipts(studentId: 30) { id studentId receiptUrl } }"
    data, errors = gql(q_receipts_self, headers=student1_headers)
    assert errors is None
    assert isinstance(data["getFeeReceipts"], list)

    # 2. Student 1 queries Student 2's receipts -> BLOCKED
    q_receipts_other = "query { getFeeReceipts(studentId: 1) { id studentId receiptUrl } }"
    data, errors = gql(q_receipts_other, headers=student1_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

def test_record_fee_payment_and_admin_updates(gql, admin_headers, student1_headers, student2_headers):
    # 1. Student 1 records fee payment for self -> Allowed
    rec_fee = """
        mutation {
            recordFeePayment(
                studentId: 30,
                semesterId: 1,
                amount: 75000.0,
                status: "paid",
                receiptUrl: "https://cloud.storage/receipts/rec_30.pdf"
            ) {
                id
                studentId
                amount
                status
                receiptUrl
            }
        }
    """
    data, errors = gql(rec_fee, headers=student1_headers)
    assert errors is None
    fee_id = data["recordFeePayment"]["id"]
    assert data["recordFeePayment"]["amount"] == 75000.0

    # 2. Student 1 attempts to record payment for Student 2 -> BLOCKED
    rec_other = """
        mutation {
            recordFeePayment(
                studentId: 1,
                semesterId: 1,
                amount: 50000.0
            ) {
                id
            }
        }
    """
    data, errors = gql(rec_other, headers=student1_headers)
    assert errors is not None
    assert "unauthorized" in errors[0]["message"].lower()

    # 3. Update Fee Status (Admin only)
    update_fee = f"""
        mutation {{
            updateFeeStatus(
                id: {fee_id},
                status: "verified",
                receiptUrl: "https://cloud.storage/receipts/verified_30.pdf"
            ) {{
                id
                status
                receiptUrl
            }}
        }}
    """
    # Student blocked from updateFeeStatus
    _, errors = gql(update_fee, headers=student1_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(update_fee, headers=admin_headers)
    assert errors is None
    assert data["updateFeeStatus"]["status"] == "verified"

def test_admin_institutional_ledger_oversight(gql, admin_headers, faculty_headers, student1_headers):
    # Admin queries all fees across the institute
    q_all_fees = "query { getAllFees { id studentId amount status } }"
    
    # Student blocked
    _, errors = gql(q_all_fees, headers=student1_headers)
    assert errors is not None

    # Faculty blocked
    _, errors = gql(q_all_fees, headers=faculty_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(q_all_fees, headers=admin_headers)
    assert errors is None
    assert len(data["getAllFees"]) > 0
