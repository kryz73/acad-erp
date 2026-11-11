import strawberry
from typing import Optional, List
from datetime import date, datetime
from sqlmodel import select
from .model import (
    Programs as ProgramModel,
    Semesters as SemesterModel,
    Batches as BatchModel,
    Courses as CourseModel,
    CourseOfferings as CourseOfferingModel,
    OfferingFaculty as OfferingFacultyModel,
    SemesterRegistrations as SemesterRegistrationModel,
    SubjectRegistrations as SubjectRegistrationModel
)
from core.security import IsAuthenticated, IsAdmin, IsStudent, is_elevated_role, check_user_ownership

@strawberry.type
class ProgramType:
    id: int
    code: str
    name: str
    department_id: int
    duration_years: int
    degree_type: str

@strawberry.type
class SemesterType:
    id: int
    program_id: int
    number: int
    start_date: date
    end_date: date
    academic_calendar_url: Optional[str]
    is_current: bool
    registration_window_start: Optional[datetime]
    registration_window_end: Optional[datetime]

@strawberry.type
class BatchType:
    id: int
    program_id: int
    name: str
    year: int
    label: str

@strawberry.type
class CourseType:
    id: int
    code: str
    name: str
    department_id: int
    credits: float
    course_type: str
    description: Optional[str]

@strawberry.type
class CourseOfferingType:
    id: int
    course_id: int
    semester_id: int
    batch_id: int
    syllabus_url: Optional[str]
    grade_submission_status: str

@strawberry.type
class OfferingFacultyType:
    offering_id: int
    faculty_id: int
    role: str

@strawberry.type
class SemesterRegistrationType:
    id: int
    student_id: int
    semester_id: int
    institute_fee_paid: bool
    hostel_fee_paid: bool
    total_credits: float
    status: str

@strawberry.type
class SubjectRegistrationType:
    id: int
    registration_id: int
    course_offering_id: int
    is_backlog: bool

@strawberry.type
class AcademicsQuery:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_program(self, info: strawberry.Info, id: int) -> Optional[ProgramType]:
        session = info.context["session"]
        p = session.get(ProgramModel, id)
        return ProgramType(**p.dict()) if p else None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_programs(self, info: strawberry.Info) -> List[ProgramType]:
        session = info.context["session"]
        programs = session.exec(select(ProgramModel)).all()
        return [ProgramType(**p.dict()) for p in programs]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_semester(self, info: strawberry.Info, id: int) -> Optional[SemesterType]:
        session = info.context["session"]
        s = session.get(SemesterModel, id)
        return SemesterType(**s.dict()) if s else None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_semesters(self, info: strawberry.Info) -> List[SemesterType]:
        session = info.context["session"]
        semesters = session.exec(select(SemesterModel)).all()
        return [SemesterType(**s.dict()) for s in semesters]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_batch(self, info: strawberry.Info, id: int) -> Optional[BatchType]:
        session = info.context["session"]
        b = session.get(BatchModel, id)
        return BatchType(**b.dict()) if b else None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_batches(self, info: strawberry.Info) -> List[BatchType]:
        session = info.context["session"]
        batches = session.exec(select(BatchModel)).all()
        return [BatchType(**b.dict()) for b in batches]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_course(self, info: strawberry.Info, id: int) -> Optional[CourseType]:
        session = info.context["session"]
        c = session.get(CourseModel, id)
        return CourseType(**c.dict()) if c else None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_courses(self, info: strawberry.Info) -> List[CourseType]:
        session = info.context["session"]
        courses = session.exec(select(CourseModel)).all()
        return [CourseType(**c.dict()) for c in courses]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_course_offering(self, info: strawberry.Info, id: int) -> Optional[CourseOfferingType]:
        session = info.context["session"]
        co = session.get(CourseOfferingModel, id)
        return CourseOfferingType(**co.dict()) if co else None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_course_offerings(self, info: strawberry.Info) -> List[CourseOfferingType]:
        session = info.context["session"]
        cos = session.exec(select(CourseOfferingModel)).all()
        return [CourseOfferingType(**co.dict()) for co in cos]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_semester_registration(self, info: strawberry.Info, id: int) -> Optional[SemesterRegistrationType]:
        session = info.context["session"]
        sr = session.get(SemesterRegistrationModel, id)
        if sr:
            if not is_elevated_role(info):
                from models.organization.model import StudentProfiles
                student = session.get(StudentProfiles, sr.student_id)
                if student:
                    check_user_ownership(info, student.user_id)
            return SemesterRegistrationType(**sr.dict())
        return None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_subject_registrations(self, info: strawberry.Info, registration_id: int) -> List[SubjectRegistrationType]:
        session = info.context["session"]
        if not is_elevated_role(info):
            sr = session.get(SemesterRegistrationModel, registration_id)
            if sr:
                from models.organization.model import StudentProfiles
                student = session.get(StudentProfiles, sr.student_id)
                if student:
                    check_user_ownership(info, student.user_id)
        srs = session.exec(select(SubjectRegistrationModel).where(SubjectRegistrationModel.registration_id == registration_id)).all()
        return [SubjectRegistrationType(**sr.dict()) for sr in srs]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_my_semester_registrations(self, info: strawberry.Info) -> List[SemesterRegistrationType]:
        session = info.context["session"]
        current_user_id = info.context.get("user_id")
        from models.organization.model import StudentProfiles
        student = session.exec(select(StudentProfiles).where(StudentProfiles.user_id == current_user_id)).first()
        if not student:
            return []
        regs = session.exec(select(SemesterRegistrationModel).where(SemesterRegistrationModel.student_id == student.id)).all()
        return [SemesterRegistrationType(**r.dict()) for r in regs]

@strawberry.type
class AcademicsMutation:
    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def create_program(self, info: strawberry.Info, code: str, name: str, department_id: int, duration_years: int, degree_type: str) -> ProgramType:
        session = info.context["session"]
        new_program = ProgramModel(code=code, name=name, department_id=department_id, duration_years=duration_years, degree_type=degree_type)
        session.add(new_program)
        session.commit()
        session.refresh(new_program)
        return ProgramType(**new_program.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def create_semester(self, info: strawberry.Info, program_id: int, number: int, start_date: date, end_date: date, is_current: bool = False, academic_calendar_url: Optional[str] = None) -> SemesterType:
        session = info.context["session"]
        new_semester = SemesterModel(program_id=program_id, number=number, start_date=start_date, end_date=end_date, is_current=is_current, academic_calendar_url=academic_calendar_url)
        session.add(new_semester)
        session.commit()
        session.refresh(new_semester)
        return SemesterType(**new_semester.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def create_batch(self, info: strawberry.Info, program_id: int, name: str, year: int, label: str) -> BatchType:
        session = info.context["session"]
        new_batch = BatchModel(program_id=program_id, name=name, year=year, label=label)
        session.add(new_batch)
        session.commit()
        session.refresh(new_batch)
        return BatchType(**new_batch.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def create_course(self, info: strawberry.Info, code: str, name: str, department_id: int, credits: float, course_type: str = "core", description: Optional[str] = None) -> CourseType:
        session = info.context["session"]
        new_course = CourseModel(code=code, name=name, department_id=department_id, credits=credits, course_type=course_type, description=description)
        session.add(new_course)
        session.commit()
        session.refresh(new_course)
        return CourseType(**new_course.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def create_course_offering(self, info: strawberry.Info, course_id: int, semester_id: int, batch_id: int, syllabus_url: Optional[str] = None) -> CourseOfferingType:
        session = info.context["session"]
        new_co = CourseOfferingModel(course_id=course_id, semester_id=semester_id, batch_id=batch_id, syllabus_url=syllabus_url)
        session.add(new_co)
        session.commit()
        session.refresh(new_co)
        return CourseOfferingType(**new_co.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def allocate_faculty_to_offering(self, info: strawberry.Info, offering_id: int, faculty_id: int, role: str = "instructor") -> OfferingFacultyType:
        session = info.context["session"]
        new_of = session.get(OfferingFacultyModel, (offering_id, faculty_id))
        if not new_of:
            new_of = OfferingFacultyModel(offering_id=offering_id, faculty_id=faculty_id, role=role)
            session.add(new_of)
            session.commit()
        else:
            new_of.role = role
            session.add(new_of)
            session.commit()
        return OfferingFacultyType(offering_id=offering_id, faculty_id=faculty_id, role=role)

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsStudent])
    def register_for_semester(self, info: strawberry.Info, student_id: int, semester_id: int) -> SemesterRegistrationType:
        session = info.context["session"]
        if not is_elevated_role(info):
            from models.organization.model import StudentProfiles
            student = session.get(StudentProfiles, student_id)
            if student:
                check_user_ownership(info, student.user_id)
            else:
                raise Exception("Student profile not found")
        existing = session.exec(
            select(SemesterRegistrationModel)
            .where(SemesterRegistrationModel.student_id == student_id)
            .where(SemesterRegistrationModel.semester_id == semester_id)
        ).first()
        if existing:
            return SemesterRegistrationType(**existing.dict())
        new_sr = SemesterRegistrationModel(student_id=student_id, semester_id=semester_id, institute_fee_paid=False, hostel_fee_paid=False, total_credits=0.0, status="pending")
        session.add(new_sr)
        session.commit()
        session.refresh(new_sr)
        return SemesterRegistrationType(**new_sr.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsStudent])
    def select_subject(self, info: strawberry.Info, registration_id: int, course_offering_id: int, is_backlog: bool = False) -> SubjectRegistrationType:
        session = info.context["session"]
        sr = session.get(SemesterRegistrationModel, registration_id)
        if not sr:
            raise Exception("Registration not found")
        if not is_elevated_role(info):
            from models.organization.model import StudentProfiles
            student = session.get(StudentProfiles, sr.student_id)
            if student:
                check_user_ownership(info, student.user_id)
            else:
                raise Exception("Student profile not found")
        existing = session.exec(
            select(SubjectRegistrationModel)
            .where(SubjectRegistrationModel.registration_id == registration_id)
            .where(SubjectRegistrationModel.course_offering_id == course_offering_id)
        ).first()
        if existing:
            existing.is_backlog = is_backlog
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return SubjectRegistrationType(**existing.dict())
        new_sub_reg = SubjectRegistrationModel(registration_id=registration_id, course_offering_id=course_offering_id, is_backlog=is_backlog)
        session.add(new_sub_reg)
        co = session.get(CourseOfferingModel, course_offering_id)
        if co:
            c = session.get(CourseModel, co.course_id)
            if c:
                sr.total_credits = (sr.total_credits or 0.0) + c.credits
                session.add(sr)
        session.commit()
        session.refresh(new_sub_reg)
        return SubjectRegistrationType(**new_sub_reg.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def update_semester_registration_status(self, info: strawberry.Info, registration_id: int, status: str, institute_fee_paid: Optional[bool] = None, hostel_fee_paid: Optional[bool] = None) -> Optional[SemesterRegistrationType]:
        session = info.context["session"]
        sr = session.get(SemesterRegistrationModel, registration_id)
        if not sr:
            return None
        sr.status = status
        if institute_fee_paid is not None:
            sr.institute_fee_paid = institute_fee_paid
        if hostel_fee_paid is not None:
            sr.hostel_fee_paid = hostel_fee_paid
        session.add(sr)
        session.commit()
        session.refresh(sr)
        return SemesterRegistrationType(**sr.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def update_registration_window(self, info: strawberry.Info, semester_id: int, start_date: str, end_date: str) -> SemesterType:
        session = info.context["session"]
        semester = session.get(SemesterModel, semester_id)
        if not semester:
            raise Exception("Semester not found")
        from datetime import datetime, timezone
        try:
            semester.registration_window_start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            semester.registration_window_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except ValueError:
            raise Exception("Invalid date format. Please use YYYY-MM-DD")
        session.add(semester)
        session.commit()
        session.refresh(semester)
        return SemesterType(**semester.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_program(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        p = session.get(ProgramModel, id)
        if p:
            session.delete(p)
            session.commit()
            return True
        return False

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_course(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        c = session.get(CourseModel, id)
        if c:
            session.delete(c)
            session.commit()
            return True
        return False

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_batch(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        b = session.get(BatchModel, id)
        if b:
            session.delete(b)
            session.commit()
            return True
        return False

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_course_offering(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        co = session.get(CourseOfferingModel, id)
        if co:
            session.delete(co)
            session.commit()
            return True
        return False

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_semester(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        s = session.get(SemesterModel, id)
        if s:
            session.delete(s)
            session.commit()
            return True
        return False
