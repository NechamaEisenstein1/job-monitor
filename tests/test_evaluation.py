import pytest

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
    job = make_job(title="מפתח/ת בוגר/ת")  # base 0.5 + medium ("בוגר") 0.15 = 0.65, no experience stated
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
        "טכנאי/ת PC": "it",
        "מפתח/ת FULLSTACK ובודק/ת אוטומציה": "software",   # the role named first decides
        "מיישם/ת הגנת סייבר": "cyber",                     # generic "it" words are a fallback
        "מנהל/ת מוצר AI": "product",
        "DevOps Engineer": "devops",
        "Data Engineer": "data",
        "נציג/ת שירות לקוחות": "other",
        "Sales Engineer": "other",
    }
    for title, expected in cases.items():
        assert s.evaluate(make_job(title=title), "run", NOW).role_type == expected, title
    # Title only: a description that mentions development does not make a role "software".
    assert s.evaluate(make_job(title="מנתח/ת מערכות", description="עבודה מול צוות פיתוח ובדיקות"),
                      "run", NOW).role_type == "it"
    # Explicit exclusions win over "מפתח"; "פיתוח" alone counts.
    assert s.evaluate(make_job(title="מפתח/ת הדרכה"), "run", NOW).role_type == "other"
    assert s.evaluate(make_job(title="מהנדס/ת לפיתוח מערכות"), "run", NOW).role_type == "software"


def test_non_tech_role_is_not_eligible_but_still_evaluated(cfg):
    ev = service(cfg).evaluate(make_job(title="נציג/ת שירות לקוחות - ללא ניסיון"), "run", NOW)
    assert ev.is_junior and ev.location_matched and not ev.is_eligible
    assert ev.rejection_reasons == ["role_not_eligible (other)"]


def test_every_tech_role_is_eligible(cfg):
    for title in ["Junior QA Engineer", "Junior Data Analyst", "Junior DevOps", "מנהל/ת מוצר - ללא ניסיון",
                  "טכנאי/ת מחשבים ללא ניסיון", "מהנדס/ת חומרה junior", "Junior Cyber Analyst"]:
        assert service(cfg).evaluate(make_job(title=title), "run", NOW).is_eligible, title


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


# ------------------------------------------------------------------ experience (junior = 0-2 years)

@pytest.mark.parametrize("requirements, junior", [
    ("ניסיון של עד שנה בפיתוח עם ANGULAR", True),          # Yael #25688
    ("ניסיון של שנתיים לפחות", True),
    ("ללא ניסיון", True),
    ("ניסיון של 3 שנים לפחות", False),
    ("3-4 שנות ניסיון - חובה", False),
    ("ניסיון של ארבע שנים לפחות", False),
    ("4+ years of experience", False),
    ("ניסיון של 5 שנים - יתרון", False),                    # advantage only -> keyword score decides (0.5)
])
def test_experience_decides_junior(cfg, requirements, junior):
    ev = service(cfg).evaluate(make_job(title="מפתח/ת תוכנה", requirements=requirements), "run", NOW)
    assert ev.is_junior is junior, (requirements, ev.matched_rules, ev.rejection_reasons)


def test_experience_overrides_junior_keywords(cfg):
    # "junior" in the title does not make a 3-year requirement junior.
    ev = service(cfg).evaluate(make_job(title="Junior Developer", requirements="3 שנות ניסיון"), "run", NOW)
    assert not ev.is_junior and any(r.startswith("experience_required") for r in ev.rejection_reasons)
    assert ev.junior_score < cfg.thresholds.junior_score  # the score agrees with the verdict


def test_low_experience_with_senior_keyword_is_not_junior(cfg):
    ev = service(cfg).evaluate(make_job(title="ראש צוות פיתוח", requirements="ניסיון של שנתיים"), "run", NOW)
    assert not ev.is_junior


def test_yael_25688_is_junior_now(cfg):
    job = make_job(title="מפתח/ת FULLSTACK ובודק/ת אוטומציה", location='ירושלים יו"ש',
                   requirements="השכלה רלוונטית\nניסיון של עד שנה בפיתוח עם ANGULAR ו- .NET CORE\n"
                                "היכרות / ניסיון בבדיקות אוטומציה- יתרון משמעותי")
    ev = service(cfg).evaluate(job, "run", NOW)
    assert ev.is_junior and ev.location_matched
