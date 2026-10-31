import type {
  ClientType, ContributionBase, ExtraKind, OfferOutcome, ReviewStatus, SickPay, StudyFundStart,
} from "../../types/salaryOffers";

export const offerTerms = {
  clientType: {
    government: "מכרז ממשלתי",
    private: "חברה פרטית",
    public: "גוף ציבורי אחר",
  } satisfies Record<ClientType, string>,

  outcome: {
    accepted: "התקבלה",
    negotiating: "במיקוח",
    declined: "נדחתה",
    not_pursued: "לא התקדמה",
  } satisfies Record<OfferOutcome, string>,

  sickPay: {
    by_law: "לפי חוק",
    full_from_day_two: "מלא מהיום השני",
    full_from_day_one: "מלא מהיום הראשון",
    half_then_full: "50% / 50% / מלא",
    other: "אחר",
  } satisfies Record<SickPay, string>,

  studyFundStart: {
    first_day: "מהיום הראשון",
    after_3_months: "אחרי 3 חודשים",
    after_6_months: "אחרי 6 חודשים",
    after_year: "אחרי שנה",
    none: "אין",
    not_stated: "לא צוין",
  } satisfies Record<StudyFundStart, string>,

  contributionBase: {
    base_salary: "מהבסיס",
    gross_salary: "מהברוטו",
  } satisfies Record<ContributionBase, string>,

  extraKind: {
    travel: "נסיעות",
    meals: "ארוחות",
    refreshments: "כיבוד",
    phone: "נייד",
    parking: "חניה",
    car: "אחזקת רכב",
    global_overtime: "שעות נוספות גלובליות",
    recovery_pay: "הבראה חודשית",
    other: "רכיב אחר",
  } satisfies Record<ExtraKind, string>,

  reviewStatus: {
    pending: "ממתינה לאישור",
    approved: "פורסמה",
    rejected: "לא אושרה",
  } satisfies Record<ReviewStatus, string>,

  detailSections: {
    holidays: { title: "חגים, מינוס וצבירה", hint: "חול המועד, ערב חג, מינוס ימים" },
    pension: { title: "פנסיה וקרן השתלמות - אחוזים", hint: "פיצויים, תגמולים, הפרשת עובד, סעיף 14" },
    recovery: { title: "דמי הבראה", hint: "לפי חוק, ימים או סכום, שנתי או חודשי" },
    overtime: { title: "שעות נוספות", hint: "גלובליות או לפי שעות בפועל" },
    training: { title: "הכשרות וקורסים", hint: "שעות, תקציב, על חשבון העבודה" },
    perks: { title: "ציוד והטבות נוספות", hint: "מחשב, ביטוח בריאות, עבודה מהבית, מענק" },
    sick: { title: "ימי מחלה - פירוט", hint: "אחוז תשלום לכל יום ומכסה בשנה" },
    negotiation: { title: "מיקוח וסכום בהצעה", hint: "השכר לפני המיקוח, הסה״כ שכתוב בהצעה" },
  },

  details: {
    stated_total: "הסה״כ שכתוב בהצעה",
    initial_base_salary: "שכר בסיס לפני המיקוח",
    sick_day_one_percent: "מחלה - יום 1 (%)",
    sick_day_two_percent: "מחלה - יום 2 (%)",
    sick_day_three_percent: "מחלה - יום 3 (%)",
    sick_full_pay_days_per_year: "ימים בשנה בתנאים אלו",
    chol_hamoed_hours: "חול המועד: שעות שיורדות",
    holiday_eve_hours: "ערב חג: שעות שיורדות",
    negative_vacation_days: "מינוס ימי חופשה מותר",
    vacation_carryover: "צבירת ימי חופשה",
    severance_percent: "פיצויים",
    employer_pension_percent: "תגמולי מעסיק (%)",
    study_fund_employer_percent: "קרן השתלמות - מעסיק (%)",
    study_fund_employee_percent: "קרן השתלמות - עובד (%)",
    study_fund_capped_at_tax_ceiling: "קרן עד תקרת המס",
    section_14: "סעיף 14",
    recovery_pay_method: "חישוב ההבראה",
    recovery_pay_value: "ימים או סכום",
    recovery_paid_monthly: "משולמת כל חודש",
    overtime_method: "שיטה",
    overtime_rate_percent: "תעריף (%)",
    training_hours_per_year: "שעות קורס בשנה",
    training_budget: "תקציב שנתי (₪)",
    training_on_work_time: "על חשבון שעות העבודה",
    training_by_tender_rules: "לפי נוהלי המכרז",
    laptop: "מחשב נייד",
    health_insurance: "ביטוח בריאות פרטי",
    remote_days_per_week: "ימים מהבית בשבוע",
    signing_bonus: "מענק חתימה (₪)",
  } as Record<string, string>,

  detailChoices: {
    up_to_3_years: "עד 3 שנים",
    paid_out: "פדיון במקום מחיקה",
    "6": "6%",
    "8.33": "8.33%",
    by_law: "לפי חוק",
    days_per_year: "מספר ימים בשנה",
    monthly_amount: "סכום חודשי",
    global: "גלובליות",
    actual_hours: "לפי שעות בפועל",
  } as Record<string, string>,

  yes: "כן",
  notStated: "לא צוין",
};
