import strawberry
from typing import Optional, List
from datetime import date
from sqlmodel import select
from .model import (
    AssessmentComponents as AssessmentComponentModel,
    StudentMarks as StudentMarksModel,
    GradeRules as GradeRuleModel,
    StudentGrades as StudentGradeModel,
    StudentSemesterResults as StudentSemesterResultModel
)
from core.security import IsAuthenticated, IsAdmin, IsFaculty, is_elevated_role, check_user_ownership

@strawberry.type
class AssessmentComponentType:
    id: int
    offering_id: int
    name: str
    max_marks: float
    weightage_pct: Optional[float]
    conducted_on: Optional[date]

@strawberry.type
class StudentMarksType:
    id: int
    component_id: int
    student_id: int
    marks_obtained: Optional[float]
    is_absent: bool
    entered_by: Optional[int]

@strawberry.type
class GradeRuleType:
    id: int
    program_id: int
    grade_letter: str
    min_percentage: float
    max_percentage: float
    grade_point: float

@strawberry.type
class StudentGradeType:
    id: int
    offering_id: int
    student_id: int
    total_marks: Optional[float]
    grade_letter: Optional[str]
    grade_point: Optional[float]
    is_published: bool

@strawberry.type
class StudentSemesterResultType:
    id: int
    student_id: int
    semester_id: int
    sgpa: Optional[float]
    cgpa: Optional[float]
    total_credits_earned: Optional[float]

@strawberry.type
class ComponentStatsType:
    component_id: int
    average: float
    median: float
    highest: float
    lowest: float
    total_students: int

@strawberry.type
class AssessmentsQuery:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_assessment_components(self, info: strawberry.Info, offering_id: int) -> List[AssessmentComponentType]:
        session = info.context["session"]
        components = session.exec(select(AssessmentComponentModel).where(AssessmentComponentModel.offering_id == offering_id)).all()
        return [AssessmentComponentType(**c.dict()) for c in components]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_student_marks(self, info: strawberry.Info, student_id: int, component_id: Optional[int] = None) -> List[StudentMarksType]:
        session = info.context["session"]
        if not is_elevated_role(info):
            from models.organization.model import StudentProfiles
            student = session.get(StudentProfiles, student_id)
            if student:
                check_user_ownership(info, student.user_id)
            else:
                raise Exception("Student profile not found")
        query = select(StudentMarksModel).where(StudentMarksModel.student_id == student_id)
        if component_id is not None:
            query = query.where(StudentMarksModel.component_id == component_id)
        marks = session.exec(query).all()
        return [StudentMarksType(**m.dict(exclude={"entered_at"})) for m in marks]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_grade_rules(self, info: strawberry.Info, program_id: int) -> List[GradeRuleType]:
        session = info.context["session"]
        rules = session.exec(select(GradeRuleModel).where(GradeRuleModel.program_id == program_id)).all()
        return [GradeRuleType(**r.dict()) for r in rules]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_student_semester_result(self, info: strawberry.Info, student_id: int, semester_id: int) -> Optional[StudentSemesterResultType]:
        session = info.context["session"]
        if not is_elevated_role(info):
            from models.organization.model import StudentProfiles
            student = session.get(StudentProfiles, student_id)
            if student:
                check_user_ownership(info, student.user_id)
            else:
                raise Exception("Student profile not found")
        result = session.exec(
            select(StudentSemesterResultModel)
            .where(StudentSemesterResultModel.student_id == student_id)
            .where(StudentSemesterResultModel.semester_id == semester_id)
        ).first()
        return StudentSemesterResultType(**result.dict()) if result else None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_offering_grades(self, info: strawberry.Info, offering_id: int) -> List[StudentGradeType]:
        session = info.context["session"]
        query = select(StudentGradeModel).where(StudentGradeModel.offering_id == offering_id)
        if not is_elevated_role(info):
            current_user_id = info.context.get("user_id")
            from models.organization.model import StudentProfiles
            student = session.exec(select(StudentProfiles).where(StudentProfiles.user_id == current_user_id)).first()
            if not student:
                return []
            query = query.where(StudentGradeModel.student_id == student.id).where(StudentGradeModel.is_published == True)
        grades = session.exec(query).all()
        return [StudentGradeType(**g.dict(exclude={"published_at"})) for g in grades]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_component_statistics(self, info: strawberry.Info, component_id: int) -> Optional[ComponentStatsType]:
        session = info.context["session"]
        marks_records = session.exec(
            select(StudentMarksModel)
            .where(StudentMarksModel.component_id == component_id)
            .where(StudentMarksModel.is_absent == False)
            .where(StudentMarksModel.marks_obtained != None)
        ).all()
        scores = [m.marks_obtained for m in marks_records if m.marks_obtained is not None]
        if not scores:
            return None
        scores.sort()
        n = len(scores)
        avg = sum(scores) / n
        med = scores[n // 2] if n % 2 != 0 else (scores[n // 2 - 1] + scores[n // 2]) / 2.0
        return ComponentStatsType(
            component_id=component_id,
            average=round(avg, 2),
            median=round(med, 2),
            highest=max(scores),
            lowest=min(scores),
            total_students=n
        )

@strawberry.type
class AssessmentsMutation:
    @strawberry.mutation(permission_classes=[IsAuthenticated, IsFaculty])
    def create_assessment_component(self, info: strawberry.Info, offering_id: int, name: str, max_marks: float, weightage_pct: Optional[float] = None, conducted_on: Optional[date] = None) -> AssessmentComponentType:
        session = info.context["session"]
        new_component = AssessmentComponentModel(offering_id=offering_id, name=name, max_marks=max_marks, weightage_pct=weightage_pct, conducted_on=conducted_on)
        session.add(new_component)
        session.commit()
        session.refresh(new_component)
        return AssessmentComponentType(**new_component.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsFaculty])
    def record_student_marks(self, info: strawberry.Info, component_id: int, student_id: int, marks_obtained: Optional[float] = None, is_absent: bool = False, entered_by: Optional[int] = None) -> StudentMarksType:
        session = info.context["session"]
        
        # Check if grades are locked
        component = session.get(AssessmentComponentModel, component_id)
        if component:
            from models.academics.model import CourseOfferings
            offering = session.get(CourseOfferings, component.offering_id)
            if offering and offering.grade_submission_status in ["submitted", "approved"]:
                raise Exception("Cannot modify marks: grades have been submitted for review.")

        # Allow updating if already exists
        existing_marks = session.exec(
            select(StudentMarksModel)
            .where(StudentMarksModel.component_id == component_id)
            .where(StudentMarksModel.student_id == student_id)
        ).first()
        
        if existing_marks:
            existing_marks.marks_obtained = marks_obtained
            existing_marks.is_absent = is_absent
            existing_marks.entered_by = entered_by
            session.add(existing_marks)
            session.commit()
            session.refresh(existing_marks)
            return StudentMarksType(**existing_marks.dict(exclude={"entered_at"}))
        else:
            new_marks = StudentMarksModel(component_id=component_id, student_id=student_id, marks_obtained=marks_obtained, is_absent=is_absent, entered_by=entered_by)
            session.add(new_marks)
            session.commit()
            session.refresh(new_marks)
            return StudentMarksType(**new_marks.dict(exclude={"entered_at"}))

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def create_grade_rule(self, info: strawberry.Info, program_id: int, grade_letter: str, min_percentage: float, max_percentage: float, grade_point: float) -> GradeRuleType:
        session = info.context["session"]
        new_rule = GradeRuleModel(program_id=program_id, grade_letter=grade_letter, min_percentage=min_percentage, max_percentage=max_percentage, grade_point=grade_point)
        session.add(new_rule)
        session.commit()
        session.refresh(new_rule)
        return GradeRuleType(**new_rule.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsFaculty])
    def calculate_and_store_grades(self, info: strawberry.Info, offering_id: int, student_id: int, total_marks: float, grade_letter: str, grade_point: float) -> StudentGradeType:
        session = info.context["session"]
        
        # Check if grades are locked
        from models.academics.model import CourseOfferings
        offering = session.get(CourseOfferings, offering_id)
        if offering and offering.grade_submission_status in ["submitted", "approved"]:
            raise Exception("Cannot modify grades: grades have been submitted for review.")

        # Simplified manual storage logic
        existing_grade = session.exec(
            select(StudentGradeModel)
            .where(StudentGradeModel.offering_id == offering_id)
            .where(StudentGradeModel.student_id == student_id)
        ).first()

        if existing_grade:
            existing_grade.total_marks = total_marks
            existing_grade.grade_letter = grade_letter
            existing_grade.grade_point = grade_point
            session.add(existing_grade)
            session.commit()
            session.refresh(existing_grade)
            return StudentGradeType(**existing_grade.dict(exclude={"published_at"}))
        else:
            new_grade = StudentGradeModel(offering_id=offering_id, student_id=student_id, total_marks=total_marks, grade_letter=grade_letter, grade_point=grade_point)
            session.add(new_grade)
            session.commit()
            session.refresh(new_grade)
            return StudentGradeType(**new_grade.dict(exclude={"published_at"}))

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_assessment_component(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        c = session.get(AssessmentComponentModel, id)
        if c:
            session.delete(c)
            session.commit()
            return True
        return False

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsFaculty])
    def submit_grades(self, info: strawberry.Info, offering_id: int) -> bool:
        session = info.context["session"]
        from models.academics.model import CourseOfferings
        offering = session.get(CourseOfferings, offering_id)
        if offering:
            offering.grade_submission_status = "submitted"
            session.add(offering)
            session.commit()
            return True
        return False

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def review_grades(self, info: strawberry.Info, offering_id: int, action: str) -> bool:
        session = info.context["session"]
        from models.academics.model import CourseOfferings
        offering = session.get(CourseOfferings, offering_id)
        if offering:
            if action == "approve":
                offering.grade_submission_status = "approved"
                # Set is_published to True for all student grades in this offering
                grades = session.exec(select(StudentGradeModel).where(StudentGradeModel.offering_id == offering_id)).all()
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                for grade in grades:
                    grade.is_published = True
                    grade.published_at = now
                    session.add(grade)
            elif action == "reject":
                offering.grade_submission_status = "revision_requested"
            session.add(offering)
            session.commit()
            return True
        return False

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_grade_rule(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        rule = session.get(GradeRuleModel, id)
        if rule:
            session.delete(rule)
            session.commit()
            return True
        return False
