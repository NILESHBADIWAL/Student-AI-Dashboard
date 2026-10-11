from database import Database
import re


DOCUMENT_SOURCES = (
    {
        "table": "attendance_rules",
        "id": "rule_id",
        "category": "Attendance Rules",
        "title": "title",
        "content": "content",
        "source": "source",
        "search_columns": (
            "title",
            "content",
            "source",
            "year",
        ),
    },
    {
        "table": "fees",
        "id": "fee_id",
        "category": "Fees",
        "title": "fee_type",
        "content": "CONCAT_WS('; ', "
                   "CONCAT('Amount: ', amount), "
                   "description)",
        "source": "academic_year",
        "search_columns": (
            "branch",
            "fee_type",
            "description",
            "academic_year",
        ),
    },
    {
        "table": "notices",
        "id": "notice_id",
        "category": "Notice",
        "title": "title",
        "content": "content",
        "source": "department",
        "search_columns": (
            "title",
            "content",
            "department",
        ),
    },
    {
        "table": "pyqs",
        "id": "pyq_id",
        "category": "PYQ",
        "title": "subject_name",
        "content": "question",
        "source": (
            "CONCAT(year, ' - ', branch, "
            "' - Semester ', semester)"
        ),
        "search_columns": (
            "subject_name",
            "question",
            "branch",
            "subject_code",
            "exam_type",
            "year",
        ),
    },
    {
        "table": "courses",
        "id": "course_id",
        "category": "Course",
        "title": "course_name",
        "content": "description",
        "source": "course_code",
        "search_columns": (
            "course_name",
            "description",
            "course_code",
            "branch",
        ),
    },
    {
        "table": "exam_rules",
        "id": "rule_id",
        "category": "Exam Rules",
        "title": "title",
        "content": "content",
        "source": "source",
        "search_columns": (
            "title",
            "content",
            "source",
            "year",
        ),
    },
    {
        "table": "faqs",
        "id": "faq_id",
        "category": "FAQ",
        "title": "question",
        "content": "answer",
        "source": "category",
        "search_columns": (
            "question",
            "answer",
            "category",
        ),
    },
    {
        "table": "library_rules",
        "id": "rule_id",
        "category": "Library Rules",
        "title": "title",
        "content": "content",
        "source": "source",
        "search_columns": (
            "title",
            "content",
            "source",
        ),
    },
    {
        "table": "hostel_rules",
        "id": "rule_id",
        "category": "Hostel Rules",
        "title": "title",
        "content": "content",
        "source": "source",
        "search_columns": (
            "title",
            "content",
            "source",
        ),
    },
    {
        "table": "scholarships",
        "id": "scholarship_id",
        "category": "Scholarship",
        "title": "name",
        "content": (
            "CONCAT_WS('; ', "
            "eligibility, "
            "amount, "
            "description, "
            "CONCAT('Deadline: ', deadline))"
        ),
        "source": "'Scholarships'",
        "search_columns": (
            "name",
            "eligibility",
            "amount",
            "description",
        ),
    },
    {
        "table": "academic_calendar",
        "id": "calendar_id",
        "category": "Academic Calendar",
        "title": "COALESCE(title, event_name)",
        "content": (
            "CONCAT_WS('; ', "
            "event_name, "
            "event_date, "
            "description)"
        ),
        "source": "academic_year",
        "search_columns": (
            "title",
            "event_name",
            "description",
            "academic_year",
        ),
    },
)


class DocumentRetriever:

    def __init__(self):
        self.database = Database()

    # ---------------------------------------------------------
    # BASIC HELPERS
    # ---------------------------------------------------------

    def _get_connection(self):
        connection = self.database.get_connection()

        if connection is None:
            raise RuntimeError(
                "Unable to connect to the chatbot database."
            )

        return connection

    def _tokenize(self, query):
        """
        Convert question into useful search terms.
        """

        stop_words = {
            "what",
            "is",
            "are",
            "the",
            "a",
            "an",
            "of",
            "for",
            "my",
            "me",
            "i",
            "in",
            "on",
            "to",
            "and",
            "how",
            "can",
            "do",
            "does",
            "tell",
            "about",
            "please",
            "give",
            "show",
            "which",
            "where",
            "when",
            "who",
        }

        words = re.findall(
            r"[a-zA-Z0-9]+",
            query.lower()
        )

        return [
            word
            for word in words
            if word not in stop_words
            and len(word) > 1
        ]

    def _build_conditions(
        self,
        search_columns,
        terms
    ):
        """
        Create SQL search conditions.

        Example:

        title LIKE %term%
        OR content LIKE %term%
        OR source LIKE %term%
        """

        conditions = []
        parameters = []

        for term in terms:
            for column in search_columns:
                conditions.append(
                    f"CAST({column} AS CHAR) LIKE %s"
                )
                parameters.append(f"%{term}%")

        return conditions, parameters

    # ---------------------------------------------------------
    # DOCUMENT SEARCH
    # ---------------------------------------------------------

    def search_documents(self, query):
        """
        Search all static/document tables.
        """

        terms = self._tokenize(query)

        if not terms:
            return []

        connection = self._get_connection()

        cursor = connection.cursor(dictionary=True)

        results = []

        try:

            for document in DOCUMENT_SOURCES:

                conditions, parameters = (
                    self._build_conditions(
                        document["search_columns"],
                        terms
                    )
                )

                if not conditions:
                    continue

                sql = f"""
                    SELECT
                        {document["id"]} AS id,

                        '{document["category"]}'
                        AS category,

                        COALESCE(
                            {document["title"]},
                            'Untitled document'
                        ) AS title,

                        COALESCE(
                            {document["content"]},
                            ''
                        ) AS content,

                        COALESCE(
                            {document["source"]},
                            'Database document'
                        ) AS source

                    FROM {document["table"]}

                    WHERE
                        {" OR ".join(conditions)}

                    LIMIT 100
                """

                cursor.execute(
                    sql,
                    parameters
                )

                rows = cursor.fetchall()

                for row in rows:

                    score = self._calculate_score(
                        query,
                        terms,
                        row
                    )

                    row["score"] = score

                    results.append(row)

        except Exception as error:

            raise RuntimeError(
                "Unable to search chatbot documents."
            ) from error

        finally:

            cursor.close()
            connection.close()

        results.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return results

    # ---------------------------------------------------------
    # RELEVANCE SCORE
    # ---------------------------------------------------------

    def _calculate_score(
        self,
        query,
        terms,
        result
    ):
        """
        Give higher scores to:

        - exact question
        - exact phrase
        - title matches
        - category matches
        - content matches
        """

        query_lower = query.lower()

        title = str(
            result.get("title") or ""
        ).lower()

        content = str(
            result.get("content") or ""
        ).lower()

        category = str(
            result.get("category") or ""
        ).lower()

        source = str(
            result.get("source") or ""
        ).lower()

        score = 0

        # Exact phrase
        if query_lower in title:
            score += 20

        if query_lower in content:
            score += 15

        # Individual terms
        for term in terms:

            if term in title:
                score += 8

            if term in category:
                score += 5

            if term in content:
                score += 3

            if term in source:
                score += 2

        # Prefer results matching multiple terms
        matched_terms = sum(
            term in (
                title + " " +
                content + " " +
                source
            )
            for term in terms
        )

        score += matched_terms * 2

        return score

    # ---------------------------------------------------------
    # STUDENT INFORMATION
    # ---------------------------------------------------------

    def get_student(self, student_id=None, roll_number=None):
        """
        Get student information.
        """

        connection = self._get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        try:

            if student_id is not None:

                cursor.execute(
                    """
                    SELECT
                        student_id,
                        roll_number,
                        name,
                        email,
                        branch,
                        semester,
                        section
                    FROM students
                    WHERE student_id = %s
                    """,
                    (student_id,)
                )

            elif roll_number is not None:

                cursor.execute(
                    """
                    SELECT
                        student_id,
                        roll_number,
                        name,
                        email,
                        branch,
                        semester,
                        section
                    FROM students
                    WHERE roll_number = %s
                    """,
                    (roll_number,)
                )

            else:
                return None

            return cursor.fetchone()

        finally:

            cursor.close()
            connection.close()

    # ---------------------------------------------------------
    # STUDENT ATTENDANCE
    # ---------------------------------------------------------

    def get_attendance(
        self,
        student_id=None,
        roll_number=None,
        course_name=None
    ):
        """
        Get attendance with course information.
        """

        connection = self._get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        try:

            sql = """
                SELECT
                    s.student_id,
                    s.roll_number,
                    s.name AS student_name,
                    s.branch,
                    s.semester,

                    c.course_id,
                    c.course_code,
                    c.course_name,

                    a.total_classes,
                    a.attended_classes,
                    a.attendance_percentage

                FROM attendance a

                INNER JOIN students s
                    ON a.student_id = s.student_id

                INNER JOIN courses c
                    ON a.course_id = c.course_id

                WHERE 1 = 1
            """

            parameters = []

            if student_id is not None:

                sql += """
                    AND s.student_id = %s
                """

                parameters.append(
                    student_id
                )

            elif roll_number is not None:

                sql += """
                    AND s.roll_number = %s
                """

                parameters.append(
                    roll_number
                )

            if course_name:

                sql += """
                    AND (
                        c.course_name LIKE %s
                        OR c.course_code LIKE %s
                    )
                """

                parameters.extend([
                    f"%{course_name}%",
                    f"%{course_name}%"
                ])

            sql += """
                ORDER BY c.course_name
            """

            cursor.execute(
                sql,
                parameters
            )

            return cursor.fetchall()

        finally:

            cursor.close()
            connection.close()

    # ---------------------------------------------------------
    # STUDENT FEES
    # ---------------------------------------------------------

    def get_student_fees(
        self,
        branch=None,
        semester=None,
        academic_year=None
    ):
        """
        Get fees for a branch/semester/year.
        """

        connection = self._get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        try:

            sql = """
                SELECT
                    fee_id,
                    branch,
                    semester,
                    fee_type,
                    amount,
                    academic_year,
                    description

                FROM fees

                WHERE 1 = 1
            """

            parameters = []

            if branch:

                sql += """
                    AND branch LIKE %s
                """

                parameters.append(
                    f"%{branch}%"
                )

            if semester is not None:

                sql += """
                    AND semester = %s
                """

                parameters.append(
                    semester
                )

            if academic_year:

                sql += """
                    AND academic_year = %s
                """

                parameters.append(
                    academic_year
                )

            sql += """
                ORDER BY fee_type
            """

            cursor.execute(
                sql,
                parameters
            )

            return cursor.fetchall()

        finally:

            cursor.close()
            connection.close()

    # ---------------------------------------------------------
    # COURSES
    # ---------------------------------------------------------

    def get_courses(
        self,
        branch=None,
        semester=None,
        course_name=None
    ):
        """
        Get courses.
        """

        connection = self._get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        try:

            sql = """
                SELECT
                    course_id,
                    course_code,
                    course_name,
                    branch,
                    semester,
                    credits,
                    description

                FROM courses

                WHERE 1 = 1
            """

            parameters = []

            if branch:

                sql += """
                    AND branch LIKE %s
                """

                parameters.append(
                    f"%{branch}%"
                )

            if semester is not None:

                sql += """
                    AND semester = %s
                """

                parameters.append(
                    semester
                )

            if course_name:

                sql += """
                    AND (
                        course_name LIKE %s
                        OR course_code LIKE %s
                    )
                """

                parameters.extend([
                    f"%{course_name}%",
                    f"%{course_name}%"
                ])

            cursor.execute(
                sql,
                parameters
            )

            return cursor.fetchall()

        finally:

            cursor.close()
            connection.close()

    # ---------------------------------------------------------
    # PYQ SEARCH
    # ---------------------------------------------------------

    def search_pyqs(
        self,
        query=None,
        subject=None,
        branch=None,
        semester=None,
        year=None
    ):
        """
        Search previous-year questions.
        """

        connection = self._get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        try:

            sql = """
                SELECT
                    pyq_id,
                    year,
                    branch,
                    semester,
                    subject_code,
                    subject_name,
                    exam_type,
                    question

                FROM pyqs

                WHERE 1 = 1
            """

            parameters = []

            if query:

                terms = self._tokenize(query)

                if terms:

                    query_conditions = []

                    for term in terms:

                        query_conditions.append(
                            """
                            (
                                subject_name LIKE %s
                                OR question LIKE %s
                                OR subject_code LIKE %s
                                OR exam_type LIKE %s
                            )
                            """
                        )

                        parameters.extend([
                            f"%{term}%",
                            f"%{term}%",
                            f"%{term}%",
                            f"%{term}%"
                        ])

                    sql += """
                        AND (
                            {}
                        )
                    """.format(
                        " OR ".join(
                            query_conditions
                        )
                    )

            if subject:

                sql += """
                    AND (
                        subject_name LIKE %s
                        OR subject_code LIKE %s
                    )
                """

                parameters.extend([
                    f"%{subject}%",
                    f"%{subject}%"
                ])

            if branch:

                sql += """
                    AND branch LIKE %s
                """

                parameters.append(
                    f"%{branch}%"
                )

            if semester is not None:

                sql += """
                    AND semester = %s
                """

                parameters.append(
                    semester
                )

            if year is not None:

                sql += """
                    AND year = %s
                """

                parameters.append(
                    year
                )

            sql += """
                ORDER BY year DESC, subject_name
            """

            cursor.execute(
                sql,
                parameters
            )

            return cursor.fetchall()

        finally:

            cursor.close()
            connection.close()

    # ---------------------------------------------------------
    # NOTICES
    # ---------------------------------------------------------

    def get_notices(
        self,
        department=None,
        important_only=False
    ):
        """
        Get college notices.
        """

        connection = self._get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        try:

            sql = """
                SELECT
                    notice_id,
                    title,
                    content,
                    notice_date,
                    department,
                    is_important

                FROM notices

                WHERE 1 = 1
            """

            parameters = []

            if department:

                sql += """
                    AND department LIKE %s
                """

                parameters.append(
                    f"%{department}%"
                )

            if important_only:

                sql += """
                    AND is_important = TRUE
                """

            sql += """
                ORDER BY
                    notice_date DESC
            """

            cursor.execute(
                sql,
                parameters
            )

            return cursor.fetchall()

        finally:

            cursor.close()
            connection.close()

    # ---------------------------------------------------------
    # ACADEMIC CALENDAR
    # ---------------------------------------------------------

    def get_calendar(
        self,
        academic_year=None
    ):
        """
        Get academic calendar events.
        """

        connection = self._get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        try:

            sql = """
                SELECT
                    calendar_id,
                    title,
                    event_name,
                    event_date,
                    description,
                    academic_year

                FROM academic_calendar

                WHERE 1 = 1
            """

            parameters = []

            if academic_year:

                sql += """
                    AND academic_year = %s
                """

                parameters.append(
                    academic_year
                )

            sql += """
                ORDER BY event_date
            """

            cursor.execute(
                sql,
                parameters
            )

            return cursor.fetchall()

        finally:

            cursor.close()
            connection.close()

    # ---------------------------------------------------------
    # SCHOLARSHIPS
    # ---------------------------------------------------------

    def get_scholarships(self):
        """
        Get all scholarships.
        """

        connection = self._get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        try:

            cursor.execute(
                """
                SELECT
                    scholarship_id,
                    name,
                    eligibility,
                    amount,
                    deadline,
                    description

                FROM scholarships

                ORDER BY deadline
                """
            )

            return cursor.fetchall()

        finally:

            cursor.close()
            connection.close()

    # ---------------------------------------------------------
    # GENERIC QUESTION SEARCH
    # ---------------------------------------------------------

    def search(self, query, student_id=None):
        """
        Main method.

        Searches:

        1. Static documents
        2. Student attendance
        3. Student information
        4. Fees
        5. Courses
        6. PYQs
        7. Notices
        8. Academic calendar
        9. Scholarships
        """

        if not query or not query.strip():
            return []

        query_lower = query.lower()

        results = []

        # -----------------------------------------------------
        # 1. NORMAL DOCUMENT SEARCH
        # -----------------------------------------------------

        results.extend(
            self.search_documents(query)
        )

        # -----------------------------------------------------
        # 2. STUDENT ATTENDANCE
        # -----------------------------------------------------

        attendance_keywords = [
            "attendance",
            "present",
            "absent",
            "attended",
            "classes",
        ]

        if any(
            keyword in query_lower
            for keyword in attendance_keywords
        ):

            attendance = self.get_attendance(
                student_id=student_id
            )

            for row in attendance:

                results.append({
                    "id": row["course_id"],
                    "category": "Student Attendance",
                    "title": row["course_name"],
                    "content": (
                        f"Student: "
                        f"{row['student_name']}; "

                        f"Course: "
                        f"{row['course_name']} "
                        f"({row['course_code']}); "

                        f"Total classes: "
                        f"{row['total_classes']}; "

                        f"Attended classes: "
                        f"{row['attended_classes']}; "

                        f"Attendance: "
                        f"{row['attendance_percentage']}%"
                    ),
                    "source": "attendance",
                    "score": 100
                })

        # -----------------------------------------------------
        # 3. FEES
        # -----------------------------------------------------

        if any(
            keyword in query_lower
            for keyword in [
                "fee",
                "fees",
                "tuition",
                "payment",
                "cost",
                "amount",
            ]
        ):

            student = None

            if student_id:
                student = self.get_student(
                    student_id=student_id
                )

            branch = (
                student["branch"]
                if student
                else None
            )

            semester = (
                student["semester"]
                if student
                else None
            )

            fees = self.get_student_fees(
                branch=branch,
                semester=semester
            )

            for row in fees:

                results.append({
                    "id": row["fee_id"],
                    "category": "Fees",
                    "title": row["fee_type"],
                    "content": (
                        f"Amount: "
                        f"{row['amount']}; "

                        f"Branch: "
                        f"{row['branch']}; "

                        f"Semester: "
                        f"{row['semester']}; "

                        f"Academic year: "
                        f"{row['academic_year']}; "

                        f"{row['description']}"
                    ),
                    "source": "fees",
                    "score": 95
                })

        # -----------------------------------------------------
        # 4. COURSES
        # -----------------------------------------------------

        if any(
            keyword in query_lower
            for keyword in [
                "course",
                "subject",
                "subjects",
                "course code",
            ]
        ):

            student = None

            if student_id:
                student = self.get_student(
                    student_id=student_id
                )

            branch = (
                student["branch"]
                if student
                else None
            )

            semester = (
                student["semester"]
                if student
                else None
            )

            courses = self.get_courses(
                branch=branch,
                semester=semester
            )

            for row in courses:

                results.append({
                    "id": row["course_id"],
                    "category": "Course",
                    "title": row["course_name"],
                    "content": (
                        f"Course code: "
                        f"{row['course_code']}; "

                        f"Credits: "
                        f"{row['credits']}; "

                        f"Branch: "
                        f"{row['branch']}; "

                        f"Semester: "
                        f"{row['semester']}; "

                        f"{row['description']}"
                    ),
                    "source": "courses",
                    "score": 90
                })

        # -----------------------------------------------------
        # 5. PYQ
        # -----------------------------------------------------

        if any(
            keyword in query_lower
            for keyword in [
                "pyq",
                "previous year",
                "previous-year",
                "question paper",
                "past question",
            ]
        ):

            pyqs = self.search_pyqs(
                query=query
            )

            for row in pyqs:

                results.append({
                    "id": row["pyq_id"],
                    "category": "PYQ",
                    "title": row["subject_name"],
                    "content": (
                        f"Year: {row['year']}; "
                        f"Branch: {row['branch']}; "
                        f"Semester: {row['semester']}; "
                        f"Subject code: "
                        f"{row['subject_code']}; "
                        f"Exam type: "
                        f"{row['exam_type']}; "
                        f"Question: "
                        f"{row['question']}"
                    ),
                    "source": "pyqs",
                    "score": 90
                })

        # -----------------------------------------------------
        # 6. NOTICES
        # -----------------------------------------------------

        if any(
            keyword in query_lower
            for keyword in [
                "notice",
                "notices",
                "announcement",
                "latest notice",
            ]
        ):

            notices = self.get_notices()

            for row in notices:

                results.append({
                    "id": row["notice_id"],
                    "category": "Notice",
                    "title": row["title"],
                    "content": row["content"],
                    "source": row["department"],
                    "score": 90
                })

        # -----------------------------------------------------
        # 7. CALENDAR
        # -----------------------------------------------------

        if any(
            keyword in query_lower
            for keyword in [
                "calendar",
                "exam date",
                "examination date",
                "semester date",
                "event",
                "when is",
            ]
        ):

            calendar = self.get_calendar()

            for row in calendar:

                results.append({
                    "id": row["calendar_id"],
                    "category": "Academic Calendar",
                    "title": (
                        row["title"]
                        or row["event_name"]
                    ),
                    "content": (
                        f"Event: "
                        f"{row['event_name']}; "

                        f"Date: "
                        f"{row['event_date']}; "

                        f"{row['description']}"
                    ),
                    "source": row["academic_year"],
                    "score": 95
                })

        # -----------------------------------------------------
        # 8. SCHOLARSHIPS
        # -----------------------------------------------------

        if any(
            keyword in query_lower
            for keyword in [
                "scholarship",
                "scholarships",
                "financial aid",
                "merit",
            ]
        ):

            scholarships = (
                self.get_scholarships()
            )

            for row in scholarships:

                results.append({
                    "id": row["scholarship_id"],
                    "category": "Scholarship",
                    "title": row["name"],
                    "content": (
                        f"Eligibility: "
                        f"{row['eligibility']}; "

                        f"Amount: "
                        f"{row['amount']}; "

                        f"Deadline: "
                        f"{row['deadline']}; "

                        f"{row['description']}"
                    ),
                    "source": "Scholarships",
                    "score": 90
                })

        # -----------------------------------------------------
        # REMOVE DUPLICATES
        # -----------------------------------------------------

        unique_results = {}

        for result in results:

            key = (
                result.get("category"),
                result.get("id")
            )

            if key not in unique_results:

                unique_results[key] = result

            elif (
                result["score"]
                > unique_results[key]["score"]
            ):

                unique_results[key] = result

        results = list(
            unique_results.values()
        )

        # -----------------------------------------------------
        # SORT
        # -----------------------------------------------------

        results.sort(
            key=lambda x: x.get(
                "score",
                0
            ),
            reverse=True
        )

        return results