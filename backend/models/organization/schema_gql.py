import strawberry
from typing import Optional, List
from datetime import date
from sqlmodel import select
from .model import Departments as DepartmentModel, FacultyProfiles as FacultyProfileModel, StudentProfiles as StudentProfileModel
from core.security import IsAuthenticated, IsAdmin, check_user_ownership, is_elevated_role

@strawberry.type
class DepartmentType:
    id: int
    code: str
    name: str
    hod_id: Optional[int]

@strawberry.type
class FacultyProfileType:
    id: int
    user_id: int
    employee_id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date]
    gender: Optional[str]
    phone: Optional[str]
    title: Optional[str]
    bio: Optional[str]
    join_date: Optional[date]
    department_id: int
    is_active: bool

@strawberry.type
class StudentProfileType:
    id: int
    user_id: int
    roll_number: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date]
    gender: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    department_id: Optional[int]
    target_cgpa: Optional[float]
    guardian_name: Optional[str]
    guardian_phone: Optional[str]
    blood_group: Optional[str]
    family_annual_income: Optional[float]
    father_name: Optional[str]
    father_profession: Optional[str]
    mother_name: Optional[str]
    mother_profession: Optional[str]
    parent_mobile: Optional[str]
    parent_email: Optional[str]
    category: Optional[str]
    marital_status: Optional[str]
    religion: Optional[str]
    home_address_city: Optional[str]
    home_address_district: Optional[str]
    home_address_state: Optional[str]
    home_address_pincode: Optional[str]
    residential_background: Optional[str]
    hostel_name: Optional[str]
    hostel_room_no: Optional[str]
    aadhar_number: Optional[str]
    abc_id: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_mobile: Optional[str]
    bank_name: Optional[str]
    bank_address: Optional[str]
    bank_account_no: Optional[str]
    local_guardian: Optional[str]
    is_active: bool

@strawberry.type
class OrganizationQuery:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_department(self, info: strawberry.Info, department_id: int) -> Optional[DepartmentType]:
        session = info.context["session"]
        dept = session.get(DepartmentModel, department_id)
        if dept:
            return DepartmentType(id=dept.id, code=dept.code, name=dept.name, hod_id=dept.hod_id)
        return None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_departments(self, info: strawberry.Info) -> List[DepartmentType]:
        session = info.context["session"]
        depts = session.exec(select(DepartmentModel)).all()
        return [DepartmentType(id=d.id, code=d.code, name=d.name, hod_id=d.hod_id) for d in depts]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_faculty_profile(self, info: strawberry.Info, profile_id: int) -> Optional[FacultyProfileType]:
        session = info.context["session"]
        faculty = session.get(FacultyProfileModel, profile_id)
        if faculty:
            return FacultyProfileType(**faculty.dict(exclude={"created_at"}))
        return None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_faculty_profiles(self, info: strawberry.Info) -> List[FacultyProfileType]:
        session = info.context["session"]
        faculties = session.exec(select(FacultyProfileModel)).all()
        return [FacultyProfileType(**f.dict(exclude={"created_at"})) for f in faculties]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_student_profile(self, info: strawberry.Info, profile_id: int) -> Optional[StudentProfileType]:
        session = info.context["session"]
        student = session.get(StudentProfileModel, profile_id)
        if student:
            if not is_elevated_role(info):
                check_user_ownership(info, student.user_id)
            return StudentProfileType(**student.dict(exclude={"created_at"}))
        return None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_my_student_profile(self, info: strawberry.Info) -> Optional[StudentProfileType]:
        session = info.context["session"]
        current_user_id = info.context.get("user_id")
        student = session.exec(select(StudentProfileModel).where(StudentProfileModel.user_id == current_user_id)).first()
        if student:
            return StudentProfileType(**student.dict(exclude={"created_at"}))
        return None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_student_profiles(self, info: strawberry.Info) -> List[StudentProfileType]:
        if not is_elevated_role(info):
            raise Exception("Unauthorized: Cannot view all students.")
        session = info.context["session"]
        students = session.exec(select(StudentProfileModel)).all()
        return [StudentProfileType(**s.dict(exclude={"created_at"})) for s in students]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_my_faculty_profile(self, info: strawberry.Info) -> Optional[FacultyProfileType]:
        session = info.context["session"]
        current_user_id = info.context.get("user_id")
        faculty = session.exec(select(FacultyProfileModel).where(FacultyProfileModel.user_id == current_user_id)).first()
        if faculty:
            return FacultyProfileType(**faculty.dict(exclude={"created_at"}))
        return None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_offering_faculty(self, info: strawberry.Info, offering_id: int) -> List[FacultyProfileType]:
        session = info.context["session"]
        from models.academics.model import OfferingFaculty as OfferingFacultyModel
        assignments = session.exec(select(OfferingFacultyModel).where(OfferingFacultyModel.offering_id == offering_id)).all()
        faculty_ids = [a.faculty_id for a in assignments]
        if not faculty_ids:
            return []
        faculties = session.exec(select(FacultyProfileModel).where(FacultyProfileModel.id.in_(faculty_ids))).all()
        return [FacultyProfileType(**f.dict(exclude={"created_at"})) for f in faculties]

@strawberry.type
class OrganizationMutation:
    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def create_department(self, info: strawberry.Info, code: str, name: str, hod_id: Optional[int] = None) -> DepartmentType:
        session = info.context["session"]
        new_dept = DepartmentModel(code=code, name=name, hod_id=hod_id)
        session.add(new_dept)
        session.commit()
        session.refresh(new_dept)
        return DepartmentType(id=new_dept.id, code=new_dept.code, name=new_dept.name, hod_id=new_dept.hod_id)

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def create_faculty_profile(self, info: strawberry.Info, user_id: int, employee_id: str, first_name: str, last_name: str, department_id: int, title: Optional[str] = None) -> FacultyProfileType:
        session = info.context["session"]
        new_faculty = FacultyProfileModel(user_id=user_id, employee_id=employee_id, first_name=first_name, last_name=last_name, department_id=department_id, title=title)
        session.add(new_faculty)
        session.commit()
        session.refresh(new_faculty)
        return FacultyProfileType(**new_faculty.dict(exclude={"created_at"}))

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def create_student_profile(
        self, info: strawberry.Info, 
        user_id: int, roll_number: str, first_name: str, last_name: str, 
        department_id: Optional[int] = None,
        target_cgpa: Optional[float] = None, blood_group: Optional[str] = None,
        family_annual_income: Optional[float] = None, father_name: Optional[str] = None,
        father_profession: Optional[str] = None, mother_name: Optional[str] = None,
        mother_profession: Optional[str] = None, parent_mobile: Optional[str] = None,
        parent_email: Optional[str] = None, category: Optional[str] = None,
        marital_status: Optional[str] = None, religion: Optional[str] = None,
        home_address_city: Optional[str] = None, home_address_district: Optional[str] = None,
        home_address_state: Optional[str] = None, home_address_pincode: Optional[str] = None,
        residential_background: Optional[str] = None, hostel_name: Optional[str] = None,
        hostel_room_no: Optional[str] = None, aadhar_number: Optional[str] = None,
        abc_id: Optional[str] = None, emergency_contact_name: Optional[str] = None,
        emergency_contact_mobile: Optional[str] = None, bank_name: Optional[str] = None,
        bank_address: Optional[str] = None, bank_account_no: Optional[str] = None,
        local_guardian: Optional[str] = None
    ) -> StudentProfileType:
        session = info.context["session"]
        new_student = StudentProfileModel(
            user_id=user_id, roll_number=roll_number, first_name=first_name, last_name=last_name,
            department_id=department_id, target_cgpa=target_cgpa, blood_group=blood_group,
            family_annual_income=family_annual_income, father_name=father_name,
            father_profession=father_profession, mother_name=mother_name,
            mother_profession=mother_profession, parent_mobile=parent_mobile,
            parent_email=parent_email, category=category, marital_status=marital_status,
            religion=religion, home_address_city=home_address_city,
            home_address_district=home_address_district, home_address_state=home_address_state,
            home_address_pincode=home_address_pincode, residential_background=residential_background,
            hostel_name=hostel_name, hostel_room_no=hostel_room_no, aadhar_number=aadhar_number,
            abc_id=abc_id, emergency_contact_name=emergency_contact_name,
            emergency_contact_mobile=emergency_contact_mobile, bank_name=bank_name,
            bank_address=bank_address, bank_account_no=bank_account_no, local_guardian=local_guardian
        )
        session.add(new_student)
        session.commit()
        session.refresh(new_student)
        return StudentProfileType(**new_student.dict(exclude={"created_at"}))

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def update_student_target_cgpa(self, info: strawberry.Info, student_id: int, target_cgpa: float) -> Optional[StudentProfileType]:
        session = info.context["session"]
        student = session.get(StudentProfileModel, student_id)
        if not student:
            return None
        if not is_elevated_role(info):
            check_user_ownership(info, student.user_id)
        student.target_cgpa = target_cgpa
        session.add(student)
        session.commit()
        session.refresh(student)
        return StudentProfileType(**student.dict(exclude={"created_at"}))

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_department(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        d = session.get(DepartmentModel, id)
        if d:
            session.delete(d)
            session.commit()
            return True
        return False
