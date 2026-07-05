from app.services.audit.auditor import audit_student


def test_fresh_student_has_zero_progress(fresh_student, cs_reqs, catalog):
    report = audit_student(fresh_student, "columbia_cs_major", cs_reqs, catalog)
    assert report.completed_count == 0
    assert report.overall_progress_pct == 0
    assert report.total_count == len(cs_reqs)


def test_midway_student_has_partial_progress(midway_student, cs_reqs, catalog):
    report = audit_student(midway_student, "columbia_cs_major", cs_reqs, catalog)
    assert 0 < report.completed_count < report.total_count
    assert 0 < report.overall_progress_pct < 1
    intro = next(r for r in report.requirements if r.name == "Introduction to Computer Science")
    assert intro.satisfied
    ds = next(r for r in report.requirements if r.name == "Data Structures")
    assert ds.satisfied
    discrete = next(r for r in report.requirements if r.name == "Discrete Mathematics")
    assert discrete.satisfied


def test_satisfied_one_of_reports_nothing_needed(midway_student, cs_reqs, catalog):
    # A satisfied one_of must not report the untaken alternatives as missing
    # or their credits as still needed.
    report = audit_student(midway_student, "columbia_cs_major", cs_reqs, catalog)
    calc = next(r for r in report.requirements if r.name == "Math: Calculus")
    assert calc.satisfied
    assert calc.missing_courses == []
    assert calc.needed_credits == 0.0


def test_unsatisfied_one_of_needs_cheapest_option(fresh_student, cs_reqs, catalog):
    report = audit_student(fresh_student, "columbia_cs_major", cs_reqs, catalog)
    calc = next(r for r in report.requirements if r.name == "Math: Calculus")
    assert not calc.satisfied
    # needed_credits should reflect ONE option, not the sum of all alternatives
    assert calc.needed_credits <= 4.0


def test_n_of_requirement_partial_credit(midway_student, cs_reqs, catalog):
    # Take one Area Foundation course → 1/3 progress
    midway_student.completed_courses.append("COMS W4701")
    report = audit_student(midway_student, "columbia_cs_major", cs_reqs, catalog)
    area = next(r for r in report.requirements if r.name == "Area Foundation Courses (pick 3)")
    assert 0 < area.progress_pct < 1
    assert not area.satisfied


def test_ms_fresh_student_audit(ms_student, ms_reqs, catalog):
    report = audit_student(ms_student, "columbia_ms_cs", ms_reqs, catalog)
    assert report.total_count == 5
    assert report.completed_count == 0


def test_waived_courses_satisfy_cards_but_earn_no_credits(session, catalog, ms_reqs, ms_student):
    from app.services.audit.auditor import audit_student

    # Waive the systems breadth via a bachelor's course; complete theory for real.
    ms_student.waived_courses = ["COMS W4118"]
    ms_student.completed_courses = ["COMS W4231"]
    report = audit_student(ms_student, "columbia_ms_cs", ms_reqs, catalog)
    by_name = {r.name: r for r in report.requirements}

    assert by_name["Breadth: Systems"].satisfied is True          # waived counts
    assert by_name["Breadth: Theory"].satisfied is True           # completed counts
    # Credit math excludes the waived course entirely.
    assert report.total_credits_completed == catalog["COMS W4231"].credits
