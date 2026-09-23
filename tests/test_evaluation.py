from dataclasses import replace

from backend.domain.services.evaluation import JobEvaluationService

from tests.conftest import NOW, make_job


def service(cfg, threshold=None):
    return JobEvaluationService.from_config(cfg, threshold)


def test_eligible_junior(cfg):
    ev = service(cfg).evaluate(make_job(title="Junior Developer"), "run", NOW)
    assert ev.is_eligible and ev.rejection_reasons == []
    assert "strong_positive:junior" in ev.matched_rules
    assert "location:primary:Jerusalem" in ev.matched_rules


def test_hebrew_keyword_and_secondary_location(cfg):
    ev = service(cfg).evaluate(make_job(title="מפתח", description="מתאים ללא ניסיון", location="בית שמש"), "run", NOW)
    assert ev.is_eligible
    assert "location:secondary:בית שמש" in ev.matched_rules


def test_senior_rejection(cfg):
    ev = service(cfg).evaluate(make_job(title="Senior Developer"), "run", NOW)
    assert not ev.is_eligible
    assert ev.rejection_reasons[0].startswith("junior_score_below_threshold")


def test_location_rejection(cfg):
    ev = service(cfg).evaluate(make_job(title="Junior Developer", location="Haifa"), "run", NOW)
    assert not ev.is_eligible
    assert ev.rejection_reasons == ["location_not_matched"]


def test_both_rejection_reasons(cfg):
    ev = service(cfg).evaluate(make_job(title="Senior Developer", location="Haifa"), "run", NOW)
    assert len(ev.rejection_reasons) == 2


def test_boundary_score_is_eligible(cfg):
    job = make_job(title="Entry Level Developer")  # base 0.5 + medium 0.15 = 0.65
    ev = service(cfg, threshold=0.65).evaluate(job, "run", NOW)
    assert ev.junior_score == 0.65 and ev.is_eligible
    assert not service(cfg, threshold=0.66).evaluate(job, "run", NOW).is_eligible


def test_location_found_in_text_only_when_field_missing(cfg):
    no_field = make_job(title="Junior Developer", location=None, description="המשרה בירושלים")
    ev = service(cfg).evaluate(no_field, "run", NOW)
    assert ev.is_eligible and "location_in_text:primary:ירושלים" in ev.matched_rules
    # An explicit location field wins over text mentions.
    elsewhere = make_job(title="Junior Developer", location="Haifa", description="לקוח בירושלים")
    assert service(cfg).evaluate(elsewhere, "run", NOW).rejection_reasons == ["location_not_matched"]


def test_keyword_needs_word_boundary(cfg):
    score, rules = service(cfg).junior_score(make_job(title="Team Leader in Misleading Co"))
    assert not any("lead" in r for r in rules)
    assert score == cfg.junior_scoring.base


def test_score_is_clamped(cfg):
    job = make_job(title="junior", description="ללא ניסיון 0-1 years entry level בוגרים")
    assert service(cfg).junior_score(job)[0] == 1.0
    assert service(cfg).junior_score(replace(job, title="senior lead architect 5+ years", description=""))[0] == 0.0


def test_hebrew_negative_keywords(cfg):
    for title in ["ארכיטקט/ית תוכנה", "מפתח/ת בכיר/ה", "ראש צוות פיתוח"]:
        ev = service(cfg).evaluate(make_job(title=title), "run", NOW)
        assert not ev.is_junior, title


def test_role_classification_title_first(cfg):
    s = service(cfg)
    cases = {
        "מפתח/ת Full Stack": "software",
        "Junior Java Developer": "software",
        "QA Automation Engineer": "qa",
        "מפתח/ת אוטומציה": "qa",
        "מהנדס/ת Embedded Real-Time": "embedded",
        "מהנדס/ת אימות שבבים": "hardware",
        "טכנאי/ת PC": "other",
    }
    for title, expected in cases.items():
        assert s.evaluate(make_job(title=title), "run", NOW).role_type == expected, title
    # Title only: a description that mentions development does not make a role "software".
    assert s.evaluate(make_job(title="מנתח/ת מערכות", description="עבודה מול צוות פיתוח ובדיקות"),
                      "run", NOW).role_type == "other"
    # Explicit exclusions win over "מפתח"; "פיתוח" alone counts.
    assert s.evaluate(make_job(title="מפתח/ת הדרכה"), "run", NOW).role_type == "other"
    assert s.evaluate(make_job(title="מהנדס/ת לפיתוח מערכות"), "run", NOW).role_type == "software"


def test_non_software_role_is_not_eligible_but_still_evaluated(cfg):
    ev = service(cfg).evaluate(make_job(title="Junior QA Engineer"), "run", NOW)
    assert ev.is_junior and ev.location_matched and not ev.is_eligible
    assert ev.rejection_reasons == ["role_not_eligible (qa)"]


def test_government_tender_detection(cfg):
    s = service(cfg)
    assert s.evaluate(make_job(title="מפתח/ת למשרד ממשלתי בירושלים"), "run", NOW).is_government_tender
    assert s.evaluate(make_job(title="Junior Developer", description="במסגרת מכרז"), "run", NOW).is_government_tender
    assert not s.evaluate(make_job(title="Junior Developer"), "run", NOW).is_government_tender


def test_rank_puts_junior_first_then_software(cfg):
    s = service(cfg)
    rank = lambda title: s.evaluate(make_job(title=title), "run", NOW).rank_score  # noqa: E731
    junior_qa, senior_dev, junior_dev = rank("Junior QA Engineer"), rank("Senior Developer"), rank("Junior Developer")
    assert junior_dev > junior_qa > senior_dev
