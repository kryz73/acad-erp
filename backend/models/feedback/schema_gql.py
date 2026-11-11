import strawberry
from typing import Optional, List
from sqlmodel import select
from .model import CourseFacultyFeedbackLinks as FeedbackLinkModel
from core.security import IsAuthenticated, IsFaculty, is_elevated_role

@strawberry.type
class FeedbackLinkType:
    id: int
    offering_id: int
    faculty_id: int
    form_url: str
    is_active: bool

@strawberry.type
class FeedbackQuery:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_course_feedback_links(self, info: strawberry.Info, offering_id: int) -> List[FeedbackLinkType]:
        session = info.context["session"]
        if not is_elevated_role(info):
            current_user_id = info.context.get("user_id")
            from models.organization.model import StudentProfiles
            from models.academics.model import SemesterRegistrations, SubjectRegistrations
            student = session.exec(select(StudentProfiles).where(StudentProfiles.user_id == current_user_id)).first()
            if not student:
                return []
            enrolled = session.exec(
                select(SubjectRegistrations)
                .join(SemesterRegistrations, SubjectRegistrations.registration_id == SemesterRegistrations.id)
                .where(SemesterRegistrations.student_id == student.id)
                .where(SubjectRegistrations.course_offering_id == offering_id)
            ).first()
            if not enrolled:
                return []
        links = session.exec(select(FeedbackLinkModel).where(FeedbackLinkModel.offering_id == offering_id)).all()
        return [FeedbackLinkType(id=l.id, offering_id=l.offering_id, faculty_id=l.faculty_id, form_url=l.form_url, is_active=l.is_active) for l in links]

@strawberry.type
class FeedbackMutation:
    @strawberry.mutation(permission_classes=[IsAuthenticated, IsFaculty])
    def create_course_feedback_link(self, info: strawberry.Info, offering_id: int, faculty_id: int, form_url: str, is_active: bool = True) -> FeedbackLinkType:
        session = info.context["session"]
        new_link = FeedbackLinkModel(offering_id=offering_id, faculty_id=faculty_id, form_url=form_url, is_active=is_active)
        session.add(new_link)
        session.commit()
        session.refresh(new_link)
        return FeedbackLinkType(id=new_link.id, offering_id=new_link.offering_id, faculty_id=new_link.faculty_id, form_url=new_link.form_url, is_active=new_link.is_active)

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsFaculty])
    def delete_course_feedback_link(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        link = session.get(FeedbackLinkModel, id)
        if link:
            session.delete(link)
            session.commit()
            return True
        return False
