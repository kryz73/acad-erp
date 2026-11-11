from datetime import date, time, datetime, timezone
from sqlmodel import Session
from core.database import engine, SQLModel
from auth.auth import pwd_context

# Import all models
from models import (
    Users, Roles, UserRoles,
    Departments, FacultyProfiles, StudentProfiles,
    Programs, Semesters, Batches, BatchEnrollments, Courses, CourseOfferings, OfferingFaculty, SemesterRegistrations, SubjectRegistrations,
    Rooms, TimetableSlots,
    AttendanceSessions, AttendanceRecords,
    AssessmentComponents, StudentMarks, GradeRules, StudentSemesterResults,
    Exams, ExamSchedules, ExamResults,
    CourseFacultyFeedbackLinks,
    StudentFees
)

# ---------------------------------------------------------------------------
# DATA EXTRACTED FROM:
#   Data/bms_students_grades.md   → 29 BMS students with SGPA/CGPA
#   Data/Course-of-study.pdf      → BMS Sem-1 course list (same as CSE Sem-1)
# ---------------------------------------------------------------------------

# BMS 2024 Batch – Semester 1 (2024–2028)
BMS_STUDENTS = [
    # (roll_no, first_name, last_name, sgpa, cgpa)
    ("2024BMS-001", "Aksh",              "Pathak",              7.65, 7.65),
    ("2024BMS-002", "Akshat",            "Tripathi",            9.52, 9.52),
    ("2024BMS-003", "Ali",               "Samin",               6.91, 6.91),
    ("2024BMS-004", "Anupam",            "Baraik",              6.65, 6.65),
    ("2024BMS-005", "Badavath",          "Sachin",              6.91, 6.91),
    ("2024BMS-006", "Challagondla",      "Rishitha",            7.83, 7.83),
    ("2024BMS-007", "Govind",            "Suman",               8.87, 8.87),
    ("2024BMS-008", "Gundlapalli",       "Raj Vardhan",         7.17, 7.17),
    ("2024BMS-009", "Jiya",              "Virpara",             8.78, 8.78),
    ("2024BMS-010", "Krishna",           "Soni",                7.78, 7.78),
    ("2024BMS-011", "Kummari",           "Vikas",               8.00, 8.00),
    ("2024BMS-012", "Lakshya",           "Mulchandani",         8.65, 8.65),
    ("2024BMS-013", "Mohnani Meet",      "Deepakkumar",         9.22, 9.22),
    ("2024BMS-014", "Neelabhro",         "Ghosh",               8.87, 8.87),
    ("2024BMS-015", "Paila Sai",         "Manjusha",            8.83, 8.83),
    ("2024BMS-016", "Prapit",            "",                    7.17, 7.17),
    ("2024BMS-017", "Pratham",           "Jaiswal",             8.04, 8.04),
    ("2024BMS-018", "Pray",              "Karia",               8.83, 8.83),
    ("2024BMS-019", "Priyanshu Sanjay",  "Kumar Jha",           7.96, 7.96),
    ("2024BMS-020", "Pulkit",            "Katariya",            8.83, 8.83),
    ("2024BMS-021", "Pushkar",           "Agrawal",             7.74, 7.74),
    ("2024BMS-022", "Rage Renu",         "Yasaswini",           6.65, 6.65),
    ("2024BMS-023", "Sai Varshith",      "Paluru",              9.00, 9.00),
    ("2024BMS-024", "Sawant Vedang",     "Amol",                7.83, 7.83),
    ("2024BMS-025", "Shreyas",           "Patil",               8.30, 8.30),
    ("2024BMS-026", "Sneh",              "Kansagara",           8.17, 8.17),
    ("2024BMS-027", "Veeravalli",        "Vinay",               9.13, 9.13),
    ("2024BMS-028", "Vijit",             "Deogade",             8.43, 8.43),
    ("2024BMS-029", "Yangoti Nandith",   "Reddy",               8.04, 8.04),
]

def _email(first: str, last: str, roll: str) -> str:
    """Generate an institutional email from name components."""
    slug = (first.split()[0] + last.split()[0] if last else first.split()[0]).lower()
    slug = slug.replace(" ", "").replace("-", "")
    num = roll.split("-")[1]  # e.g. '001'
    return f"{slug}{num}@iiitmg.ac.in"

# ---------------------------------------------------------------------------
# BMS Semester-1 courses (from Course-of-study.pdf, page 2)
# These are SHARED with CSE/EE/ES students in first year
# ---------------------------------------------------------------------------
BMS_SEM1_COURSES = [
    # (code, name,                                    credits, dept_code)
    ("EE101",  "Fundamentals of Electrical and Electronics Engineering", 4.0, "EE"),
    ("ES101",  "Engineering Physics",                                    4.0, "ES"),
    ("ES102",  "Engineering Mathematics",                                4.0, "ES"),
    ("EE102",  "Engineering Design Principles",                          3.0, "EE"),
    ("CS101",  "Principles of Computer Programming",                     4.0, "CS"),
    ("HS101",  "Freshman Skills",                                        2.0, "HS"),
    ("HS102",  "Sports and Physical Education",                          2.0, "HS"),
]

# Grade rules for BMS program (standard 10-point scale)
GRADE_RULES = [
    ("O",  90.0, 100.0, 10.0),
    ("A+", 80.0,  89.9,  9.0),
    ("A",  70.0,  79.9,  8.0),
    ("B+", 60.0,  69.9,  7.0),
    ("B",  50.0,  59.9,  6.0),
    ("C",  45.0,  49.9,  5.0),
    ("P",  40.0,  44.9,  4.0),
    ("F",   0.0,  39.9,  0.0),
]

# Faculty for BMS – fabricated but realistic
BMS_FACULTY = [
    # (emp_id, first, last, title, dept_code, email)
    ("FAC-CS-01",  "Rahul",   "Sharma",     "Dr.",  "CS", "rahul.sharma@iiitmg.ac.in"),
    ("FAC-EE-01",  "Ananya",  "Verma",      "Dr.",  "EE", "ananya.verma@iiitmg.ac.in"),
    ("FAC-ES-01",  "Suresh",  "Gupta",      "Dr.",  "ES", "suresh.gupta@iiitmg.ac.in"),
    ("FAC-HS-01",  "Priya",   "Nair",       "Prof.","HS", "priya.nair@iiitmg.ac.in"),
]

# Map course code prefix → faculty index in BMS_FACULTY
COURSE_FACULTY_MAP = {
    "CS":  0,
    "EE":  1,
    "ES":  2,
    "HS":  3,
}

DEFAULT_PASSWORD = "1234"


def seed_db():
    print("Dropping existing tables...")
    SQLModel.metadata.drop_all(engine)
    print("Creating tables...")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        print("Seeding data...")
        import random

        # 1. ROLES
        role_admin = Roles(name="Admin", description="System Administrator")
        role_faculty = Roles(name="Faculty", description="Teaching Staff")
        role_student = Roles(name="Student", description="Enrolled Student")
        session.add_all([role_admin, role_faculty, role_student])
        session.commit()

        # 2. USERS
        admin_user = Users(email="admin@college.edu", password_hash=pwd_context.hash("password123"), is_active=True)
        faculty_user = Users(email="faculty@college.edu", password_hash=pwd_context.hash("password123"), is_active=True)
        student_user = Users(email="student@college.edu", password_hash=pwd_context.hash("password123"), is_active=True)
        session.add_all([admin_user, faculty_user, student_user])
        session.commit()

        # Link Roles
        session.add(UserRoles(user_id=admin_user.id, role_id=role_admin.id))
        session.add(UserRoles(user_id=faculty_user.id, role_id=role_faculty.id))
        session.add(UserRoles(user_id=student_user.id, role_id=role_student.id))
        session.commit()

        # 3. DEPARTMENTS & PROGRAMS
        depts = {
            "CS": Departments(code="CSE", name="Computer Science"),
            "EE": Departments(code="EE", name="Electrical Engineering"),
            "ES": Departments(code="ES", name="Engineering Sciences"),
            "HS": Departments(code="HS", name="Humanities"),
        }
        session.add_all(depts.values())
        session.commit()

        prog_bcs = Programs(code="BCS", name="B.Tech CS", department_id=depts["CS"].id, duration_years=4, degree_type="UG")
        session.add(prog_bcs)
        session.commit()

        # Current Semester
        sem_1 = Semesters(
            program_id=prog_bcs.id, 
            number=1, 
            start_date=date(2026, 8, 1), 
            end_date=date(2026, 12, 15), 
            is_current=True,
            registration_window_start=datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc),
            registration_window_end=datetime(2026, 8, 15, 23, 59, tzinfo=timezone.utc)
        )
        session.add(sem_1)
        session.commit()

        batch_1 = Batches(program_id=prog_bcs.id, name="Class of 2030", year=2026, label="BCS-2026")
        session.add(batch_1)
        session.commit()

        # 4. PROFILES
        demo_faculty_profile = FacultyProfiles(
            user_id=faculty_user.id,
            employee_id="FAC-DEMO",
            first_name="John",
            last_name="Doe",
            department_id=depts["CS"].id,
            title="Associate Professor"
        )
        session.add(demo_faculty_profile)
        session.commit()

        faculty_profiles = [demo_faculty_profile]
        for i, (code, dept) in enumerate(depts.items()):
            email = f"faculty_{code.lower()}@college.edu"
            u = Users(email=email, password_hash=pwd_context.hash("password123"), is_active=True)
            session.add(u)
            session.commit()
            session.add(UserRoles(user_id=u.id, role_id=role_faculty.id))
            session.commit()

            fp = FacultyProfiles(
                user_id=u.id,
                employee_id=f"FAC{i:03d}",
                first_name=f"Prof.{code}",
                last_name="Expert",
                department_id=dept.id,
                title="Professor"
            )
            faculty_profiles.append(fp)
        session.add_all(faculty_profiles)
        session.commit()

        bms_faculty_profiles = []
        for emp_id, first, last, title, dept_code, fac_email in BMS_FACULTY:
            fac_u = Users(email=fac_email, password_hash=pwd_context.hash("password123"), is_active=True)
            session.add(fac_u)
            session.commit()
            session.add(UserRoles(user_id=fac_u.id, role_id=role_faculty.id))
            session.commit()
            bfp = FacultyProfiles(
                user_id=fac_u.id,
                employee_id=emp_id,
                first_name=first,
                last_name=last,
                department_id=depts[dept_code].id,
                title=title
            )
            bms_faculty_profiles.append(bfp)
        session.add_all(bms_faculty_profiles)
        session.commit()

        bms_student_profiles = []
        for roll, first, last, sgpa, cgpa in BMS_STUDENTS:
            email = _email(first, last, roll)
            stu_u = Users(email=email, password_hash=pwd_context.hash(DEFAULT_PASSWORD), is_active=True)
            session.add(stu_u)
            session.commit()
            session.add(UserRoles(user_id=stu_u.id, role_id=role_student.id))
            session.commit()

            sp = StudentProfiles(
                user_id=stu_u.id,
                roll_number=roll,
                first_name=first,
                last_name=last,
                department_id=depts["CS"].id,
                target_cgpa=8.0
            )
            bms_student_profiles.append(sp)
        session.add_all(bms_student_profiles)
        session.commit()

        student_profile = StudentProfiles(
            user_id=student_user.id,
            roll_number="26BCS001",
            first_name="Jane",
            last_name="Smith",
            department_id=depts["CS"].id,
            target_cgpa=8.5
        )
        session.add(student_profile)
        session.commit()
        all_students = bms_student_profiles + [student_profile]

        for sp in all_students:
            session.add(BatchEnrollments(student_id=sp.id, batch_id=batch_1.id, semester_id=sem_1.id))
        session.commit()

        # 5. GRADE RULES
        grade_rule_objs = []
        for g_grade, g_min, g_max, g_points in GRADE_RULES:
            grade_rule_objs.append(GradeRules(
                program_id=prog_bcs.id,
                grade_letter=g_grade, 
                min_percentage=g_min, 
                max_percentage=g_max, 
                grade_point=g_points
            ))
        session.add_all(grade_rule_objs)
        session.commit()

        # 6. COURSES & OFFERINGS
        courses = []
        for code, name, credits, dept_prefix in BMS_SEM1_COURSES:
            c = Courses(code=code, name=name, department_id=depts[dept_prefix].id, credits=credits, course_type="core")
            courses.append(c)
        session.add_all(courses)
        session.commit()

        offerings = []
        for c in courses:
            off = CourseOfferings(course_id=c.id, semester_id=sem_1.id, batch_id=batch_1.id)
            offerings.append(off)
        session.add_all(offerings)
        session.commit()

        for i, off in enumerate(offerings):
            dept_code = courses[i].code[:2]
            if dept_code not in ["CS", "EE", "ES", "HS"]: dept_code = "CS"
            fac_idx = COURSE_FACULTY_MAP.get(dept_code, 0)
            faculty = bms_faculty_profiles[fac_idx]
            session.add(OfferingFaculty(offering_id=off.id, faculty_id=faculty.id, role="instructor"))
        session.commit()

        # 7. REGISTRATIONS
        for sp in all_students:
            sr = SemesterRegistrations(
                student_id=sp.id, 
                semester_id=sem_1.id, 
                institute_fee_paid=True, 
                hostel_fee_paid=True, 
                total_credits=sum(c.credits for c in courses), 
                status="approved"
            )
            session.add(sr)
            session.commit()

            for off in offerings:
                sub_reg = SubjectRegistrations(registration_id=sr.id, course_offering_id=off.id, is_backlog=False)
                session.add(sub_reg)
            session.commit()

        # 8. SCHEDULING (Timetable) & ROOMS
        rooms = [
            Rooms(code="LT-1", capacity=100, building="Admin Block"),
            Rooms(code="LT-2", capacity=100, building="Admin Block"),
            Rooms(code="LT-3", capacity=100, building="Admin Block"),
            Rooms(code="Lab-1", capacity=50, building="CS Block"),
            Rooms(code="Lab-2", capacity=50, building="EE Block"),
        ]
        session.add_all(rooms)
        session.commit()

        for day in range(1, 6):
            for i, off in enumerate(offerings):
                if (i + day) % 2 == 0:
                    slot = TimetableSlots(
                        offering_id=off.id, 
                        room_id=rooms[i % len(rooms)].id, 
                        day_of_week=day, 
                        start_time=time(9 + i, 0), 
                        end_time=time(10 + i, 0), 
                        effective_from=date(2026, 8, 1)
                    )
                    session.add(slot)
        session.commit()

        # 9. ATTENDANCE & MARKS
        for i, off in enumerate(offerings):
            # Assessment components
            comps = [
                AssessmentComponents(offering_id=off.id, name="Assignment 1", max_marks=20.0, weightage_pct=10.0),
                AssessmentComponents(offering_id=off.id, name="Quiz 1", max_marks=30.0, weightage_pct=15.0),
                AssessmentComponents(offering_id=off.id, name="Midterm", max_marks=100.0, weightage_pct=25.0),
            ]
            session.add_all(comps)
            session.commit()

            # Feedback links
            # Get the faculty assigned to this offering
            offering_faculty = next((of for of in session.query(OfferingFaculty).filter(OfferingFaculty.offering_id == off.id).all()), None)
            fac_id = offering_faculty.faculty_id if offering_faculty else bms_faculty_profiles[0].id
            
            session.add(CourseFacultyFeedbackLinks(
                offering_id=off.id,
                faculty_id=fac_id,
                form_url="https://forms.gle/sampleformlink",
                is_active=True
            ))
            session.commit()

            # Attendance sessions
            sessions_list = []
            for d in range(1, 11):
                sess = AttendanceSessions(
                    offering_id=off.id,
                    session_date=date(2026, 8, d + 10),
                    start_time=time(9, 0),
                    end_time=time(10, 0),
                    conducted_by=bms_faculty_profiles[0].id
                )
                sessions_list.append(sess)
            session.add_all(sessions_list)
            session.commit()

            for sp in all_students:
                # Attendance
                for sess in sessions_list:
                    status = "Present" if random.random() > 0.15 else "Absent"
                    session.add(AttendanceRecords(session_id=sess.id, student_id=sp.id, status=status))

                # Marks
                for comp in comps:
                    marks = random.uniform(comp.max_marks * 0.6, comp.max_marks * 0.95)
                    session.add(StudentMarks(component_id=comp.id, student_id=sp.id, marks_obtained=round(marks, 1), is_absent=False))
        session.commit()

        # 10. EXAMS
        exam_main = Exams(semester_id=sem_1.id, name="End-Sem Dec 2026", exam_type="Final", status="scheduled")
        session.add(exam_main)
        session.commit()

        for i, c in enumerate(courses):
            exam_sched = ExamSchedules(
                exam_id=exam_main.id, 
                course_id=c.id, 
                room_id=rooms[i % len(rooms)].id, 
                exam_date=date(2026, 12, i + 1), 
                start_time=time(9, 0), 
                end_time=time(12, 0)
            )
            session.add(exam_sched)
            session.commit()

            for sp in all_students:
                marks = random.uniform(50.0, 95.0)
                session.add(ExamResults(
                    exam_schedule_id=exam_sched.id,
                    student_id=sp.id,
                    marks_obtained=round(marks, 1),
                    status="Present"
                ))
        session.commit()

        # 11. FEES
        for sp in all_students:
            fee1 = StudentFees(student_id=sp.id, semester_id=sem_1.id, fee_type="Tuition", amount=120000.0, due_date=date(2026, 8, 15), status="paid")
            fee2 = StudentFees(student_id=sp.id, semester_id=sem_1.id, fee_type="Hostel", amount=35000.0, due_date=date(2026, 8, 15), status="paid" if random.random() > 0.1 else "pending")
            session.add_all([fee1, fee2])
        session.commit()

        # Previous Semester Results (for CGPA testing)
        sem_0 = Semesters(program_id=prog_bcs.id, number=0, start_date=date(2026, 1, 1), end_date=date(2026, 5, 15), is_current=False)
        session.add(sem_0)
        session.commit()

        # Populate StudentSemesterResults based on their true SGPA/CGPA from data
        for sp in bms_student_profiles:
            matching_student = next((s for s in BMS_STUDENTS if s[0] == sp.roll_number), None)
            if matching_student:
                _, _, _, sgpa, cgpa = matching_student
                sem_res = StudentSemesterResults(student_id=sp.id, semester_id=sem_1.id, sgpa=sgpa, cgpa=cgpa, total_credits_earned=23.0)
                session.add(sem_res)
        
        # Jane Smith
        sem_res_0 = StudentSemesterResults(student_id=student_profile.id, semester_id=sem_0.id, sgpa=8.2, cgpa=8.2, total_credits_earned=18.0)
        sem_res_1 = StudentSemesterResults(student_id=student_profile.id, semester_id=sem_1.id, sgpa=8.8, cgpa=8.5, total_credits_earned=23.0)
        session.add_all([sem_res_0, sem_res_1])
        session.commit()

        print("Database Seeded Successfully with rich test data!")

if __name__ == "__main__":
    seed_db()
