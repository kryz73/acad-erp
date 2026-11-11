import pytest

def test_rooms_crud_and_rbac(gql, admin_headers, faculty_headers, student1_headers):
    # 1. Create Room (Admin only)
    create_room = """
        mutation {
            createRoom(
                code: "SEMINAR-HALL-A",
                capacity: 150,
                building: "Academic Complex",
                roomType: "Auditorium"
            ) {
                id
                code
                capacity
                building
            }
        }
    """
    # Student blocked
    _, errors = gql(create_room, headers=student1_headers)
    assert errors is not None

    # Faculty blocked
    _, errors = gql(create_room, headers=faculty_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(create_room, headers=admin_headers)
    assert errors is None
    room_id = data["createRoom"]["id"]
    assert data["createRoom"]["code"] == "SEMINAR-HALL-A"
    assert data["createRoom"]["capacity"] == 150

    # 2. Query Room & Rooms (All authenticated)
    q_room = f"query {{ getRoom(id: {room_id}) {{ id code capacity }} }}"
    data, errors = gql(q_room, headers=student1_headers)
    assert errors is None
    assert data["getRoom"]["code"] == "SEMINAR-HALL-A"

    q_all = "query { getRooms { id code } }"
    data, errors = gql(q_all, headers=student1_headers)
    assert errors is None
    codes = [r["code"] for r in data["getRooms"]]
    assert "SEMINAR-HALL-A" in codes
    assert "LT-1" in codes

    # 3. Delete Room (Admin only)
    del_room = f"mutation {{ deleteRoom(id: {room_id}) }}"
    # Student blocked
    _, errors = gql(del_room, headers=student1_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(del_room, headers=admin_headers)
    assert errors is None
    assert data["deleteRoom"] is True

def test_timetable_slots_and_logistics(gql, admin_headers, faculty_headers, student1_headers):
    # 1. Create Timetable Slot (Admin only)
    create_slot = """
        mutation {
            createTimetableSlot(
                offeringId: 1,
                dayOfWeek: 2,
                startTime: "11:00:00",
                endTime: "11:55:00",
                effectiveFrom: "2026-08-01",
                roomId: 1
            ) {
                id
                offeringId
                dayOfWeek
                startTime
                endTime
            }
        }
    """
    # Student blocked
    _, errors = gql(create_slot, headers=student1_headers)
    assert errors is not None

    # Faculty blocked
    _, errors = gql(create_slot, headers=faculty_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(create_slot, headers=admin_headers)
    assert errors is None
    slot_id = data["createTimetableSlot"]["id"]
    assert data["createTimetableSlot"]["dayOfWeek"] == 2

    # 2. Query timetable slot
    q_slot = f"query {{ getTimetableSlot(id: {slot_id}) {{ id offeringId dayOfWeek }} }}"
    data, errors = gql(q_slot, headers=student1_headers)
    assert errors is None
    assert data["getTimetableSlot"]["id"] == slot_id

    # Query all slots for offering 1
    q_slots = "query { getTimetableSlots(offeringId: 1) { id offeringId dayOfWeek } }"
    data, errors = gql(q_slots, headers=student1_headers)
    assert errors is None
    assert any(s["id"] == slot_id for s in data["getTimetableSlots"])

    # 3. Delete timetable slot (Admin only)
    del_slot = f"mutation {{ deleteTimetableSlot(id: {slot_id}) }}"
    # Student blocked
    _, errors = gql(del_slot, headers=student1_headers)
    assert errors is not None

    # Admin allowed
    data, errors = gql(del_slot, headers=admin_headers)
    assert errors is None
    assert data["deleteTimetableSlot"] is True
