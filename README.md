# AcadERP 🎓

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Strawberry GraphQL](https://img.shields.io/badge/Strawberry-GraphQL-e535ab.svg?logo=graphql&logoColor=white)](https://strawberry.rocks)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg?logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4+-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com)

A modern, full-stack **Academic Enterprise Resource Planning (ERP)** platform architected for higher-education institutions and universities. AcadERP features a modular, **Domain-Driven Design (DDD)** backend powered by **FastAPI** and **Strawberry GraphQL**, paired with a responsive, role-tailored frontend built on **Next.js 14 (App Router)** and **Tailwind CSS**.

The system enforces strict **Role-Based Access Control (RBAC)** across three primary tiers: **Administration**, **Faculty**, and **Students**, providing complete data isolation, automated grade calculations, attendance tracking, and timetable logistics.

---

## 📑 Table of Contents

- [Key Highlights](#-key-highlights)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Core Modules (Domain-Driven Design)](#-core-modules-domain-driven-design)
- [User Roles & Portals](#-user-roles--portals)
- [Project Structure](#-project-structure)
- [Quickstart with Docker](#-quickstart-with-docker-recommended)
- [Manual Local Setup](#-manual-local-setup)
- [Default Demo Credentials](#-default-demo-credentials)
- [GraphQL API & RBAC Testing](#-graphql-api--rbac-testing)
- [The Development Team](#-the-development-team)
- [License](#-license)

---

## 🌟 Key Highlights

- **Strict Role-Based Access Control (RBAC)**: Field-level and resolver-level authorization guaranteeing cross-role data privacy (students cannot view peers' grades; faculty are scoped to their assigned courses; administrators oversee system-wide workflows).
- **Single Unified GraphQL Endpoint**: Powered by Strawberry GraphQL with strong typing, schema stitching across 9 academic domains, and integrated interactive GraphiQL playground.
- **Academic Logistics & Timetables**: Dynamic scheduling mapping course offerings to lecture theatres/labs, days of the week, and recurring time slots with collision prevention.
- **Continuous Evaluation & Grading Engine**: Configurable component weightages (quizzes, assignments, midterms, endterms), automatic letter-grade mapping (standard 10-point scale: `O`, `A+`, `A`, `B+`, `B`, `C`, `P`, `F`), and semester SGPA/CGPA computation.
- **Attendance Monitoring**: Lecture and lab attendance logging with automatic detection and alerts for students dropping below the mandatory 75% threshold.
- **Semester Registration & Backlogs**: Self-service student registration workflow supporting elective selections, backlog enrollments, credit ceilings, and institute/hostel fee status validation.
- **Turnkey Realistic Seeding**: Includes a comprehensive database seeder populated with real academic structures, curriculum data, and student cohorts (modeled after ABV-IIITM Gwalior curriculum standards).

---

## 🏛 System Architecture

AcadERP follows a clean, decoupled three-tier architecture:

```mermaid
flowchart TD
    subgraph ClientLayer ["Client Layer (Next.js 14)"]
        A["Student Portal (/student)"]
        B["Faculty Portal (/faculty)"]
        C["Admin Portal (/admin)"]
        AuthUI["Auth & Login (/login)"]
    end

    subgraph APILayer ["API & Business Logic (FastAPI + Strawberry)"]
        Gate["CORS & Request Pipeline"]
        AuthRouter["OAuth2 / JWT Auth Handler (/auth)"]
        GQL["Strawberry GraphQL Router (/graphql)"]
        RBAC["Security & Permission Engine (IsAdmin, IsFaculty, IsStudent, OwnerGuard)"]
        DomainResolvers["Domain Resolvers\n(Identity, Academics, Scheduling, Attendance, Assessments, Exams, Feedback, Finance)"]
    end

    subgraph DataLayer ["Data & Storage Layer"]
        SQLModelORM["SQLModel ORM"]
        Postgres[("PostgreSQL Database")]
        Alembic["Alembic Migrations"]
    end

    ClientLayer -->|"HTTP / REST (Tokens)"| AuthRouter
    ClientLayer -->|"GraphQL Queries & Mutations (Bearer JWT)"| GQL
    GQL --> Gate
    Gate --> RBAC
    RBAC --> DomainResolvers
    DomainResolvers --> SQLModelORM
    SQLModelORM --> Postgres
    Alembic -.-> Postgres
```

---

## 💻 Tech Stack

| Layer | Technology | Description |
|---|---|---|
| **Frontend** | [Next.js 14](https://nextjs.org) (App Router), React 18, TypeScript | Modern, component-based user interface with responsive layouts |
| **Styling & UI** | [Tailwind CSS](https://tailwindcss.com), [Lucide React](https://lucide.dev) | Crisp design system, utility-first styling, and clean icons |
| **API Runtime** | [FastAPI](https://fastapi.tiangolo.com), Uvicorn | High-performance asynchronous Python web framework |
| **GraphQL Engine** | [Strawberry GraphQL](https://strawberry.rocks) | Code-first Python GraphQL library providing type safety and custom permissions |
| **Database & ORM** | [PostgreSQL 15](https://www.postgresql.org), [SQLModel](https://sqlmodel.tiangolo.com) | Relational database combined with SQLAlchemy + Pydantic modeling |
| **Security & Auth** | OAuth2 Bearer, [Argon2](https://github.com/hynek/argon2-cffi) (`passlib`), [JWT](https://github.com/mpdavis/python-jose) (`python-jose`) | Industry-standard password hashing and cryptographically signed tokens |
| **Data Migrations** | [Alembic](https://alembic.sqlalchemy.org) | Database schema migrations and versioning |
| **Containerization** | [Docker](https://www.docker.com), Docker Compose | Declarative multi-container configuration for backend, frontend, and database |

---

## 📦 Core Modules (Domain-Driven Design)

The system is organized into 9 domain-specific modules in the backend (`backend/models/`):

1. **Identity & Access** (`models/identity`):
   - Secure user identity (`Users`), password hashing via Argon2, role definitions (`Roles`), and user-role mapping (`UserRoles`).
2. **Organization** (`models/organization`):
   - Institute hierarchy: `Departments`, `Programs` (B.Tech, M.Tech, Ph.D.), `Batches`, and comprehensive profiles (`FacultyProfiles`, `StudentProfiles` with guardian, banking, and demographic records).
3. **Academics** (`models/academics`):
   - Curriculum catalog (`Courses`), active terms (`Semesters`), course offerings (`CourseOfferings`), faculty assignments (`OfferingFaculty`), and student semester/subject registration (`SemesterRegistrations`, `SubjectRegistrations`).
4. **Scheduling & Facilities** (`models/scheduling`):
   - Physical room inventory (`Rooms` with capacity and buildings) and timetable scheduling (`TimetableSlots` mapping offerings to days and time windows).
5. **Attendance Tracking** (`models/attendance`):
   - Daily lecture and lab sessions (`AttendanceSessions`) and individual student records (`AttendanceRecords` tracking Present/Absent/Late status).
6. **Assessments & Grading** (`models/assessments`):
   - Flexible component definitions (`AssessmentComponents` e.g., Quizzes, Midterms, Assignments), raw scores (`StudentMarks`), grading scales (`GradeRules`), and official results (`StudentSemesterResults` for SGPA/CGPA).
7. **Examinations** (`models/exams`):
   - Centralized exam periods (`Exams`), course exam dates and room allotments (`ExamSchedules`), and verified marks (`ExamResults`).
8. **Feedback** (`models/feedback`):
   - Course and faculty review infrastructure (`CourseFacultyFeedbackLinks`) allowing contextual evaluation forms tied to enrolled courses.
9. **Finance** (`models/finance`):
   - Institutional ledgers (`StudentFees`) tracking Tuition and Hostel fee schedules, due dates, and payment statuses (Paid/Pending/Partial).

---

## 👥 User Roles & Portals

### 1. Student Portal (`/student`)
- **Dashboard**: High-level snapshot of enrolled courses, upcoming timetable slots, fee clearance, and current semester GPA.
- **My Profile**: View personal, academic, guardian, and institutional identification details.
- **My Courses**: Enrolled course syllabus, assigned faculty, credit counts, and component breakdown.
- **Timetable**: Weekly interactive timetable with class hours, room numbers, and faculty details.
- **Grades & GPA**: Current and historical semester SGPAs, cumulative CGPA, and a **Target CGPA Goal Planner** calculating the required SGPA in future semesters.
- **Attendance**: Real-time attendance percentage per course with visual indicators alerting if attendance drops near or below 75%.
- **Examinations**: Published schedule of upcoming midterm and end-semester exams with hall allocations.
- **Fee Status**: Ledger of tuition and hostel fees, payment status, and due dates.
- **Registration**: Online semester registration and subject enrollment (including backlog handling).

### 2. Faculty Portal (`/faculty`)
- **Dashboard**: Teaching schedule for the day, assigned course offerings, and total enrolled students.
- **My Courses**: Comprehensive management view for each assigned course offering (`/faculty/courses/[offeringId]`).
- **Timetable**: Personalized weekly teaching timetable detailing lecture theatres and lab slots.
- **Student Roster & Alerts**: Class directory with automated flags for students falling below the mandatory 75% attendance threshold.
- **Attendance Management**: Record and modify daily lecture and lab attendance.
- **Assessments & Marks Entry**: Define evaluation components and enter raw marks for assignments, quizzes, and examinations.
- **Examinations**: Assigned invigilation duties, examination schedules, and student mark submissions.

### 3. Administration Portal (`/admin`)
- **Overview**: High-level institutional metrics (total enrolled students, active faculty, running courses, fee collection statistics).
- **Course & Curriculum Management**: Create courses, define credit structures, configure course offerings, and assign faculty.
- **Registrations Oversight**: Review, approve, or flag student semester registration requests.
- **Grade Approval & Results Publication**: Review faculty-submitted grades, apply institution-wide grade boundaries, and officially publish semester results.
- **Examinations Central**: Orchestrate master examination schedules, slot allocations, and hall assignments.
- **Feedback Administration**: Configure and distribute feedback forms to students for enrolled courses.
- **Finance Administration**: Monitor institutional revenue, tuition/hostel fee reconciliation, and clearance statuses.

---

## 📂 Project Structure

```text
acad-erp/
├── docker-compose.yml             # Multi-container orchestration (DB, API, Frontend)
├── implementation_plan.md         # Original system design & specification
├── features.md                    # Detailed backend feature inventory
├── ACAD erp rule_features.md      # Access control & RBAC business rules
├── LICENSE                        # MIT License
│
├── backend/                       # FastAPI + Strawberry GraphQL Service
│   ├── Dockerfile                 # Backend container definition
│   ├── requirements-backend.txt   # Python dependencies
│   ├── main.py                    # FastAPI entrypoint, CORS & GraphQL mounting
│   ├── seed_db.py                 # Comprehensive database seeder script
│   ├── reset_db.py                # Database wipe and schema rebuild utility
│   ├── graphql_layer_test.py      # Automated GraphQL RBAC permission test suite
│   ├── .keys.example              # Template environment configuration file
│   ├── auth/                      # Authentication routes & token generator
│   │   └── auth.py                # OAuth2 token login, Argon2 password verify, JWT
│   ├── core/                      # Application core configuration
│   │   ├── config.py              # Pydantic Settings management
│   │   ├── database.py            # SQLModel database engine & session dependency
│   │   └── security.py            # Strawberry GraphQL permission classes (RBAC)
│   └── models/                    # Domain-Driven Design schema & GraphQL modules
│       ├── academics/             # Courses, Semesters, Offerings, Registrations
│       ├── assessments/           # Components, Marks, GradeRules, Results
│       ├── attendance/            # Attendance Sessions & Records
│       ├── exams/                 # Exams, ExamSchedules, ExamResults
│       ├── feedback/              # Course & Faculty Feedback links
│       ├── finance/               # StudentFees & Ledger
│       ├── identity/              # Users, Roles, UserRoles
│       ├── organization/          # Departments, Programs, Student/Faculty Profiles
│       ├── scheduling/            # Rooms, TimetableSlots
│       └── schema_gql.py          # Master GraphQL Query & Mutation schema
│
├── front/                         # Next.js 14 Frontend Application
│   ├── Dockerfile                 # Frontend container definition
│   ├── package.json               # Node.js dependencies & scripts
│   ├── tailwind.config.js         # Tailwind CSS configuration
│   ├── tsconfig.json              # TypeScript compiler configuration
│   └── src/
│       ├── app/                   # Next.js App Router
│       │   ├── page.tsx           # Smart root redirect based on user role
│       │   ├── login/page.tsx     # Sign-in page with 1-click demo switcher
│       │   ├── admin/             # Admin portal pages (courses, exams, finance, etc.)
│       │   ├── faculty/           # Faculty portal pages (courses, attendance, marks, etc.)
│       │   └── student/           # Student portal pages (grades, timetable, profile, etc.)
│       ├── components/layout/     # UI shell: Sidebar, TopBar, AuthGuard
│       ├── context/               # AuthContext managing JWTs and active roles
│       ├── hooks/                 # Custom React hooks (e.g., useStudentProfile)
│       └── lib/                   # GraphQL request wrapper & shared queries
│
├── db/                            # Database Schemas & Migrations
│   ├── schema.sql                 # Pure SQL schema definition
│   ├── requirements-db.txt        # Database migration dependencies
│   └── alembic/                   # Alembic environment and migration scripts
│
└── Data/                          # Sample Curriculum & Grading Data
    ├── bms_students_grades.md     # Reference student grades and SGPA/CGPA records
    ├── Course-of-study.pdf        # Institute course and syllabus structures
    └── Lecture Schedule .pdf      # Master lecture schedule reference
```

---

## 🚀 Quickstart with Docker (Recommended)

The simplest way to run the entire stack (PostgreSQL, FastAPI Backend, and Next.js Frontend) is using **Docker Compose**:

### 1. Clone and Navigate to the Repository
```bash
git clone https://github.com/karyxx/acad-erp.git
cd acad-erp
```

### 2. Launch the Application Containers
```bash
docker compose up --build
```

Docker Compose spins up:
- **Database** (`postgres:15-alpine`) on port `5432`
- **FastAPI Backend** on `http://localhost:8000` (GraphiQL available at `http://localhost:8000/graphql`)
- **Next.js Frontend** on `http://localhost:3000`

### 3. Seed the Database
In a new terminal window, execute the database seeder inside the running backend container:
```bash
docker compose exec backend python seed_db.py
```
*This populates the database with departments, faculty members, BMS/CSE student cohorts, timetable slots, courses, attendance sessions, exam schedules, and fee ledgers.*

### 4. Access the Application
Open your browser and navigate to **[http://localhost:3000](http://localhost:3000)** to sign in!

---

## 🛠 Manual Local Setup

If you prefer to run the services directly on your host machine for development:

### Prerequisites
- **Python** 3.12+
- **Node.js** 18.x or 20.x and **npm**
- **PostgreSQL** 14+ running locally

---

### Step 1: Database Setup
Create a PostgreSQL database and user:
```sql
CREATE USER acad_user WITH PASSWORD 'supersecret';
CREATE DATABASE acad_erp_db OWNER acad_user;
GRANT ALL PRIVILEGES ON DATABASE acad_erp_db TO acad_user;
```

---

### Step 2: Backend Setup
1. Open a terminal and navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate    # On Windows: venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements-backend.txt
   ```
4. Configure your environment:
   Create a file named `.keys` in `backend/` (or copy `.keys.example`):
   ```ini
   DATABASE_URL="postgresql://acad_user:supersecret@localhost:5432/acad_erp_db"
   SECRET_KEY="my_super_secret_dev_key_12345"
   ALGORITHM="HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   ```
5. Seed the database with initial test data:
   ```bash
   python seed_db.py
   ```
6. Start the FastAPI development server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   *The API will be live at `http://localhost:8000` and the interactive GraphQL playground at `http://localhost:8000/graphql`.*

---

### Step 3: Frontend Setup
1. Open another terminal and navigate to `front/`:
   ```bash
   cd front
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Ensure the environment variables point to your API:
   Verify `front/.env.local`:
   ```ini
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
4. Start the Next.js development server:
   ```bash
   npm run dev
   ```
5. Visit **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 🔑 Default Demo Credentials

The database seeder provisions pre-configured accounts across all roles. You can click on the demo account buttons on the login page or enter the credentials below:

| Role | Email | Password | Scope & Access |
|---|---|---|---|
| **Admin** | `admin@college.edu` | `password123` | Full access to institutional settings, courses, grade approvals, and finance |
| **Faculty** | `faculty@college.edu` | `password123` | Access to assigned classes, timetable, attendance marking, and grade entries |
| **Student (Demo)** | `student@college.edu` | `password123` | Student portal demo profile (Jane Smith, 26BCS001) |
| **Faculty (CS)** | `rahul.sharma@iiitmg.ac.in` | `password123` | Computer Science instructor profile |
| **Student (BMS)** | `akshpathak001@iiitmg.ac.in` | `1234` | BMS student profile (Roll: `2024BMS-001`) |
| **Student (BMS)** | `akshattripathi002@iiitmg.ac.in` | `1234` | BMS student profile (Roll: `2024BMS-002`) |

*(All 29 BMS students listed in `Data/bms_students_grades.md` are seeded with institutional emails `<firstname><lastname><rollnum>@iiitmg.ac.in` and password `1234`).*

---

## 🧪 GraphQL API & RBAC Testing

### Interactive GraphQL Playground
Visit **[http://localhost:8000/graphql](http://localhost:8000/graphql)** while the backend is running to access the Strawberry GraphiQL interface. To execute authenticated queries, add an `Authorization` header:
```json
{
  "Authorization": "Bearer <YOUR_JWT_ACCESS_TOKEN>"
}
```

### Automated RBAC Verification Suite
AcadERP includes an automated security test runner that verifies permission enforcement across all roles:

```bash
cd backend
python graphql_layer_test.py
```

This runs queries and mutations against `Admin`, `Faculty`, `Student`, and `Unauthenticated` callers, verifying that data boundaries are strictly respected:

```text
Operation Name                      | Admin      | Faculty    | Student    | Unauth    
-------------------------------------------------------------------------------------
getUsers                            | ALLOWED    | BLOCKED    | BLOCKED    | BLOCKED   
getDepartments                      | ALLOWED    | ALLOWED    | ALLOWED    | BLOCKED   
getStudentProfiles                  | ALLOWED    | ALLOWED    | BLOCKED    | BLOCKED   
getStudentProfile (Self)            | ALLOWED    | ALLOWED    | ALLOWED    | BLOCKED   
getPrograms                         | ALLOWED    | ALLOWED    | ALLOWED    | BLOCKED   
getSemesterReg (Self)               | ALLOWED    | BLOCKED    | ALLOWED    | BLOCKED   
getRooms                            | ALLOWED    | ALLOWED    | ALLOWED    | BLOCKED   
getStudentMarks (Self)              | ALLOWED    | ALLOWED    | ALLOWED    | BLOCKED   
getExamResults (Self)               | ALLOWED    | ALLOWED    | ALLOWED    | BLOCKED   
getStudentFeeStatus (Self)          | ALLOWED    | BLOCKED    | ALLOWED    | BLOCKED   
-------------------------------------------------------------------------------------
createProgram (Admin Only)          | ALLOWED    | BLOCKED    | BLOCKED    | BLOCKED   
recordStudentMarks (Faculty Only)   | ALLOWED    | ALLOWED    | BLOCKED    | BLOCKED   
registerForSemester (Student Self)  | ALLOWED    | BLOCKED    | ALLOWED    | BLOCKED   
updateUser (Self)                   | ALLOWED    | BLOCKED    | ALLOWED    | BLOCKED   
```

---

## 👥 The Development Team

AcadERP was designed and developed by:

- **Neelabhro Ghosh** (`2024BMS-014`) — *Backend Developer*
- **Pulkit Katariya** (`2024BMS-020`) — *Backend Developer*
- **Pray Karia** (`2024BMS-018`) — *Database Management & Schemas*
- **Anupam Baraik** (`2024BMS-004`) — *Frontend Developer*
- **Sachin Badavath** (`2024BMS-005`) — *Frontend Developer*

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) — see the `LICENSE` file for details.
