import strawberry
from typing import Optional, List
from datetime import date, time
from sqlmodel import select
from .model import (
    Exams as ExamModel,
    ExamSchedules as ExamScheduleModel,
    ExamResults as ExamResultModel
)
from core.security import IsAuthenticated, IsAdmin, IsFaculty, is_elevated_role

@strawberry.type
class ExamType:
    id: int
    semester_id: int
    name: str
    exam_type: str
    status: str

@strawberry.type
class ExamScheduleType:
    id: int
    exam_id: int
    course_id: int
    room_id: Optional[int]
    exam_date: date
    start_time: time
    end_time: time

@strawberry.type
class ExamResultType:
    id: int
    exam_schedule_id: int
    student_id: int
    marks_obtained: Optional[float]
    is_absent: bool
    is_published: bool

@strawberry.type
class ExamsQuery:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_exam(self, info: strawberry.Info, id: int) -> Optional[ExamType]:
        session = info.context["session"]
        exam = session.get(ExamModel, id)
        return ExamType(**exam.dict()) if exam else None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_exams(self, info: strawberry.Info, semester_id: Optional[int] = None) -> List[ExamType]:
        session = info.context["session"]
        query = select(ExamModel)
        if semester_id is not None:
            query = query.where(ExamModel.semester_id == semester_id)
        exams = session.exec(query).all()
        return [ExamType(**e.dict()) for e in exams]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_exam_schedules(self, info: strawberry.Info, exam_id: int) -> List[ExamScheduleType]:
        session = info.context["session"]
        schedules = session.exec(select(ExamScheduleModel).where(ExamScheduleModel.exam_id == exam_id)).all()
        return [ExamScheduleType(**s.dict()) for s in schedules]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_exam_results(self, info: strawberry.Info, exam_schedule_id: int) -> List[ExamResultType]:
        session = info.context["session"]
        query = select(ExamResultModel).where(ExamResultModel.exam_schedule_id == exam_schedule_id)
        if not is_elevated_role(info):
            current_user_id = info.context.get("user_id")
            from models.organization.model import StudentProfiles
            student_profile = session.exec(select(StudentProfiles).where(StudentProfiles.user_id == current_user_id)).first()
            if student_profile:
                query = query.where(ExamResultModel.student_id == student_profile.id)
            else:
                return []
        results = session.exec(query).all()
        return [ExamResultType(**r.dict()) for r in results]

@strawberry.type
class ExamsMutation:
    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def create_exam(self, info: strawberry.Info, semester_id: int, name: str, exam_type: str, status: str = "scheduled") -> ExamType:
        session = info.context["session"]
        new_exam = ExamModel(semester_id=semester_id, name=name, exam_type=exam_type, status=status)
        session.add(new_exam)
        session.commit()
        session.refresh(new_exam)
        return ExamType(**new_exam.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def create_exam_schedule(self, info: strawberry.Info, exam_id: int, course_id: int, exam_date: date, start_time: time, end_time: time, room_id: Optional[int] = None) -> ExamScheduleType:
        session = info.context["session"]
        new_schedule = ExamScheduleModel(exam_id=exam_id, course_id=course_id, exam_date=exam_date, start_time=start_time, end_time=end_time, room_id=room_id)
        session.add(new_schedule)
        session.commit()
        session.refresh(new_schedule)
        return ExamScheduleType(**new_schedule.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsFaculty])
    def record_exam_result(self, info: strawberry.Info, exam_schedule_id: int, student_id: int, marks_obtained: Optional[float] = None, is_absent: bool = False, is_published: bool = False) -> ExamResultType:
        session = info.context["session"]
        existing_result = session.exec(
            select(ExamResultModel)
            .where(ExamResultModel.exam_schedule_id == exam_schedule_id)
            .where(ExamResultModel.student_id == student_id)
        ).first()

        if existing_result:
            existing_result.marks_obtained = marks_obtained
            existing_result.is_absent = is_absent
            existing_result.is_published = is_published
            session.add(existing_result)
            session.commit()
            session.refresh(existing_result)
            return ExamResultType(**existing_result.dict())
        else:
            new_result = ExamResultModel(exam_schedule_id=exam_schedule_id, student_id=student_id, marks_obtained=marks_obtained, is_absent=is_absent, is_published=is_published)
            session.add(new_result)
            session.commit()
            session.refresh(new_result)
            return ExamResultType(**new_result.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_exam(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        e = session.get(ExamModel, id)
        if e:
            session.delete(e)
            session.commit()
            return True
        return False

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_exam_schedule(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        s = session.get(ExamScheduleModel, id)
        if s:
            session.delete(s)
            session.commit()
            return True
        return False

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_exam_result(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        r = session.get(ExamResultModel, id)
        if r:
            session.delete(r)
            session.commit()
            return True
        return False
