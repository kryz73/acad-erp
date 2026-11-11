import strawberry
from typing import Optional, List
from sqlmodel import select
from .model import StudentFees as StudentFeeModel
from core.security import IsAuthenticated, IsAdmin, IsStudent, is_elevated_role, check_user_ownership

@strawberry.type
class StudentFeeType:
    id: int
    student_id: int
    semester_id: int
    amount: float
    status: str
    receipt_url: Optional[str]

@strawberry.type
class FinanceQuery:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_student_fee_status(self, info: strawberry.Info, student_id: int, semester_id: Optional[int] = None) -> List[StudentFeeType]:
        session = info.context["session"]
        if not is_elevated_role(info):
            from models.organization.model import StudentProfiles
            student = session.get(StudentProfiles, student_id)
            if student:
                check_user_ownership(info, student.user_id)
            else:
                raise Exception("Student profile not found")
        query = select(StudentFeeModel).where(StudentFeeModel.student_id == student_id)
        if semester_id is not None:
            query = query.where(StudentFeeModel.semester_id == semester_id)
        fees = session.exec(query).all()
        return [StudentFeeType(id=f.id, student_id=f.student_id, semester_id=f.semester_id, amount=f.amount, status=f.status, receipt_url=f.receipt_url) for f in fees]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_fee_receipts(self, info: strawberry.Info, student_id: int) -> List[StudentFeeType]:
        session = info.context["session"]
        if not is_elevated_role(info):
            from models.organization.model import StudentProfiles
            student = session.get(StudentProfiles, student_id)
            if student:
                check_user_ownership(info, student.user_id)
            else:
                raise Exception("Student profile not found")
        fees = session.exec(
            select(StudentFeeModel)
            .where(StudentFeeModel.student_id == student_id)
            .where(StudentFeeModel.receipt_url != None)
        ).all()
        return [StudentFeeType(id=f.id, student_id=f.student_id, semester_id=f.semester_id, amount=f.amount, status=f.status, receipt_url=f.receipt_url) for f in fees]

    @strawberry.field(permission_classes=[IsAuthenticated, IsAdmin])
    def get_all_fees(self, info: strawberry.Info, semester_id: Optional[int] = None) -> List[StudentFeeType]:
        session = info.context["session"]
        query = select(StudentFeeModel)
        if semester_id is not None:
            query = query.where(StudentFeeModel.semester_id == semester_id)
        fees = session.exec(query).all()
        return [StudentFeeType(id=f.id, student_id=f.student_id, semester_id=f.semester_id, amount=f.amount, status=f.status, receipt_url=f.receipt_url) for f in fees]

@strawberry.type
class FinanceMutation:
    @strawberry.mutation(permission_classes=[IsAuthenticated, IsStudent])
    def record_fee_payment(self, info: strawberry.Info, student_id: int, semester_id: int, amount: float, status: str = "unpaid", receipt_url: Optional[str] = None) -> StudentFeeType:
        session = info.context["session"]
        if not is_elevated_role(info):
            from models.organization.model import StudentProfiles
            student = session.get(StudentProfiles, student_id)
            if student:
                check_user_ownership(info, student.user_id)
        existing_fee = session.exec(
            select(StudentFeeModel)
            .where(StudentFeeModel.student_id == student_id)
            .where(StudentFeeModel.semester_id == semester_id)
        ).first()

        if existing_fee:
            existing_fee.amount = amount
            existing_fee.status = status
            existing_fee.receipt_url = receipt_url
            session.add(existing_fee)
            session.commit()
            session.refresh(existing_fee)
            return StudentFeeType(id=existing_fee.id, student_id=existing_fee.student_id, semester_id=existing_fee.semester_id, amount=existing_fee.amount, status=existing_fee.status, receipt_url=existing_fee.receipt_url)
        else:
            new_fee = StudentFeeModel(student_id=student_id, semester_id=semester_id, amount=amount, status=status, receipt_url=receipt_url)
            session.add(new_fee)
            session.commit()
            session.refresh(new_fee)
            return StudentFeeType(id=new_fee.id, student_id=new_fee.student_id, semester_id=new_fee.semester_id, amount=new_fee.amount, status=new_fee.status, receipt_url=new_fee.receipt_url)

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def update_fee_status(self, info: strawberry.Info, id: int, status: Optional[str] = None, receipt_url: Optional[str] = None) -> Optional[StudentFeeType]:
        session = info.context["session"]
        fee = session.get(StudentFeeModel, id)
        if not fee:
            return None
        if status is not None:
            fee.status = status
        if receipt_url is not None:
            fee.receipt_url = receipt_url
        session.add(fee)
        session.commit()
        session.refresh(fee)
        return StudentFeeType(id=fee.id, student_id=fee.student_id, semester_id=fee.semester_id, amount=fee.amount, status=fee.status, receipt_url=fee.receipt_url)

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_student_fee(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        f = session.get(StudentFeeModel, id)
        if f:
            session.delete(f)
            session.commit()
            return True
        return False
