import strawberry
from typing import Optional, List
from datetime import date, time
from sqlmodel import select
from .model import AttendanceSessions, AttendanceRecords
from core.security import IsAuthenticated, IsFaculty, is_elevated_role, check_user_ownership

@strawberry.type
class AttendanceSessionType:
    id: int
    offering_id: int
    session_date: date
    start_time: time
    end_time: time
    conducted_by: int

@strawberry.type
class AttendanceRecordType:
    id: int
    student_id: int
    status: str

@strawberry.type
class LowAttendanceStudent:
    student_id: int
    attendance_percentage: float

@strawberry.type
class AttendanceQuery:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def session_attendance(self, info: strawberry.Info, session_id: int) -> List[AttendanceRecordType]:
        session = info.context["session"]
        records = session.exec(select(AttendanceRecords).where(AttendanceRecords.session_id == session_id)).all()
        return [AttendanceRecordType(id=r.id, student_id=r.student_id, status=r.status) for r in records]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_offering_attendance_sessions(self, info: strawberry.Info, offering_id: int) -> List[AttendanceSessionType]:
        session = info.context["session"]
        sessions = session.exec(select(AttendanceSessions).where(AttendanceSessions.offering_id == offering_id)).all()
        return [
            AttendanceSessionType(
                id=s.id,
                offering_id=s.offering_id,
                session_date=s.session_date,
                start_time=s.start_time,
                end_time=s.end_time,
                conducted_by=s.conducted_by
            )
            for s in sessions
        ]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_my_attendance_records(self, info: strawberry.Info, student_id: int) -> List[AttendanceRecordType]:
        session = info.context["session"]
        if not is_elevated_role(info):
            from models.organization.model import StudentProfiles
            student = session.get(StudentProfiles, student_id)
            if student:
                check_user_ownership(info, student.user_id)
            else:
                raise Exception("Student profile not found")
        records = session.exec(select(AttendanceRecords).where(AttendanceRecords.student_id == student_id)).all()
        return [AttendanceRecordType(id=r.id, student_id=r.student_id, status=r.status) for r in records]

    @strawberry.field(permission_classes=[IsAuthenticated, IsFaculty])
    def get_low_attendance_students(self, info: strawberry.Info, offering_id: int, threshold_pct: float = 75.0) -> List[LowAttendanceStudent]:
        session = info.context["session"]
        
        sessions = session.exec(select(AttendanceSessions).where(AttendanceSessions.offering_id == offering_id)).all()
        session_ids = [s.id for s in sessions]
        
        if not session_ids:
            return []
            
        records = session.exec(select(AttendanceRecords).where(AttendanceRecords.session_id.in_(session_ids))).all()
        
        student_attendance = {}
        for r in records:
            if r.student_id not in student_attendance:
                student_attendance[r.student_id] = {"present": 0, "total": 0}
            student_attendance[r.student_id]["total"] += 1
            if r.status.lower() == "present":
                student_attendance[r.student_id]["present"] += 1
                
        low_attendance_students = []
        for student_id, stats in student_attendance.items():
            if stats["total"] > 0:
                pct = (stats["present"] / stats["total"]) * 100
                if pct < threshold_pct:
                    low_attendance_students.append(LowAttendanceStudent(student_id=student_id, attendance_percentage=pct))
                    
        return low_attendance_students

@strawberry.type
class AttendanceMutation:
    @strawberry.mutation(permission_classes=[IsAuthenticated, IsFaculty])
    def create_attendance_session(self, info: strawberry.Info, offering_id: int, session_date: date, start_time: time, end_time: time, conducted_by: int) -> AttendanceSessionType:
        session = info.context["session"]
        new_sess = AttendanceSessions(offering_id=offering_id, session_date=session_date, start_time=start_time, end_time=end_time, conducted_by=conducted_by)
        session.add(new_sess)
        session.commit()
        session.refresh(new_sess)
        return AttendanceSessionType(
            id=new_sess.id,
            offering_id=new_sess.offering_id,
            session_date=new_sess.session_date,
            start_time=new_sess.start_time,
            end_time=new_sess.end_time,
            conducted_by=new_sess.conducted_by
        )

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsFaculty])
    def mark_attendance(self, info: strawberry.Info, session_id: int, student_id: int, status: str) -> AttendanceRecordType:
        session = info.context["session"]
        existing = session.exec(
            select(AttendanceRecords)
            .where(AttendanceRecords.session_id == session_id)
            .where(AttendanceRecords.student_id == student_id)
        ).first()
        if existing:
            existing.status = status
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return AttendanceRecordType(id=existing.id, student_id=existing.student_id, status=existing.status)
        else:
            rec = AttendanceRecords(session_id=session_id, student_id=student_id, status=status)
            session.add(rec)
            session.commit()
            session.refresh(rec)
            return AttendanceRecordType(id=rec.id, student_id=rec.student_id, status=rec.status)
