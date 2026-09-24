# העלאה לאוויר (Production)

המטרה: אתר ציבורי עם כתובת קבועה, כניסה עם Google ועם אימייל וסיסמה, והתראות, בלי תלות במחשב שלך.

## הארכיטקטורה

| חלק | איפה | עלות |
|---|---|---|
| האתר וה-API (אותו שרת, אותו Dockerfile) | **Render**: Web Service | חינם (נרדם אחרי 15 דקות בלי ביקורים); Starter כ-7$ לחודש, תמיד ער |
| בסיס הנתונים (PostgreSQL) | **Neon** | חינם, ללא תפוגה |
| הסריקה היומית ב-07:00 | **GitHub Actions** (כבר קיים ב-`.github/workflows`) | חינם |
| מיילים (אימות, התראות, פניות) | Gmail SMTP או כל שרת SMTP | חינם עד כ-500 מיילים ביום |

הסודות (סיסמאות ומפתחות) נשמרים רק בהגדרות של Render ו-GitHub, לעולם לא בקוד. הפיתוח המקומי ממשיך לעבוד עם `.env` ו-SQLite כמו היום.

---

## 1. בסיס נתונים: Neon (כ-5 דקות)

1. נכנסים ל-https://neon.tech ולוחצים **Sign up** (אפשר עם GitHub).
2. **Create project**: שם `job-monitor`, גרסת Postgres **16**, אזור **AWS Europe Central (Frankfurt)**.
3. במסך **Connection Details** מסמנים **Pooled connection** ומעתיקים את ה-connection string. הוא נראה כך:
   `postgresql://USER:PASSWORD@ep-xxxx-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require`
   זו הכתובת שנקראת בהמשך `DATABASE_URL`. שמרי אותה במקום בטוח.

### העברת הנתונים הקיימים (המשרות והמשתמשים שכבר יש לך)
ב-Command Prompt, בתיקיית הפרויקט:
```cmd
set DATABASE_URL=<ה-connection string מ-Neon>
.venv\Scripts\python -m backend.cli copy-data --source sqlite:///job_monitor.db
set DATABASE_URL=
```
הפקודה יוצרת את הטבלאות ב-Neon ומעתיקה את כל הנתונים. היא מסרבת לרוץ אם ב-Neon כבר יש נתונים, כך שאי אפשר לשכפל או לדרוס נתונים בטעות.

---

## 2. האתר: Render (כ-10 דקות)

1. נכנסים ל-https://render.com, לוחצים **Sign up** עם חשבון GitHub, ומאשרים ל-Render לגשת למאגר `job-monitor`.
2. **New +** ← **Blueprint** ← בוחרים את המאגר `NechamaEisenstein1/job-monitor` ← **Connect**.
   Render קורא את `render.yaml` ומציע ליצור שירות בשם `job-monitor`.
3. ממלאים את הערכים שהוא מבקש:
   | משתנה | ערך |
   |---|---|
   | `DATABASE_URL` | ה-connection string מ-Neon |
   | `PUBLIC_BASE_URL` | בינתיים `https://job-monitor.onrender.com` (מתקנים בשלב 4) |
   | `ADMIN_EMAILS` | הכתובת שלך, זו שאיתה תיכנסי (למשל `you@gmail.com`) |
   | `CONTACT_EMAIL` | כתובת שתופיע במדיניות הפרטיות לבקשות מחיקה |
   | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | ריק בינתיים (שלב 3) |
   | `GOOGLE_SITE_VERIFICATION` | ריק בינתיים (שלב 6) |
   | `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | שלב 5 (אפשר ריק בינתיים) |
4. **Apply**. הבנייה הראשונה לוקחת כמה דקות. בסיומה מופיעה בראש העמוד הכתובת הקבועה, למשל `https://job-monitor-ab12.onrender.com`.
5. אם הכתובת שונה ממה שכתבת: **Environment** ← מעדכנים את `PUBLIC_BASE_URL` לכתובת המדויקת (בלי `/` בסוף) ← **Save Changes**. השירות ייפרס מחדש.
6. בודקים: הכתובת פותחת את דף הבית, ו-`<כתובת>/healthz` מחזיר `{"status":"ok"}`.

> בתוכנית החינמית, הביקור הראשון אחרי 15 דקות בלי תנועה לוקח כ-50 שניות, כי השרת מתעורר. לאתר אמיתי מומלץ לשדרג ל-**Starter** (Settings ← Instance Type).

---

## 3. כניסה עם Google (כ-10 דקות)

**למה זה לא עבד עד עכשיו:** הקוד מוכן, אבל לא קיים OAuth client ב-Google, ו-`GOOGLE_CLIENT_ID` ו-`GOOGLE_CLIENT_SECRET` לא הוגדרו. בלעדיהם השרת מכבה את Google ומסתיר את הכפתור.

1. https://console.cloud.google.com ← בחירת פרויקט (למעלה) ← **New Project** ← שם `job-monitor` ← **Create**.
2. **APIs & Services** ← **OAuth consent screen** (או **Google Auth Platform** ← **Branding**):
   - **User type: External**
   - **App name:** מוניטור משרות. **User support email:** המייל שלך.
   - **App logo:** לא חובה (העלאת לוגו מחייבת אישור של Google, אז עדיף לדלג).
   - **Application home page:** `<הכתובת שלך>/`
   - **Privacy policy:** `<הכתובת שלך>/privacy`. **Terms of service:** `<הכתובת שלך>/terms`
   - **Authorized domains:** הדומיין שלך. ב-Render זה `job-monitor-ab12.onrender.com`. Google עשוי לבקש שהדומיין יאומת ב-Search Console, וזה בדיוק שלב 6.
   - **Scopes:** רק `openid`, `.../auth/userinfo.email`, `.../auth/userinfo.profile`. אלה הרשאות בסיסיות שלא מצריכות תהליך אימות מול Google.
3. **Credentials** (או **Clients**) ← **Create credentials** ← **OAuth client ID**:
   - **Application type: Web application**, שם: `job-monitor web`
   - **Authorized JavaScript origins:**
     - `https://job-monitor-ab12.onrender.com` (הכתובת שלך)
     - `http://localhost:8000` (לפיתוח מקומי)
   - **Authorized redirect URIs**, בדיוק כך:
     - `https://job-monitor-ab12.onrender.com/api/auth/google/callback`
     - `http://localhost:8000/api/auth/google/callback`
   - **Create** ← מעתיקים את **Client ID** ואת **Client secret**.
4. ב-Render ← **Environment** ← `GOOGLE_CLIENT_ID` ו-`GOOGLE_CLIENT_SECRET` ← **Save Changes**.
   (לפיתוח מקומי: מוסיפים את אותם שני ערכים ל-`.env` ומפעילים מחדש את השרת.)
5. **חשוב:** ב-**OAuth consent screen** ← **Audience** ← **Publish app** ← **Confirm**.
   כל עוד האפליקציה במצב *Testing*, רק משתמשי בדיקה שהוגדרו ידנית יכולים להתחבר.
6. בודקים באתר: "המשך עם Google" ← בחירת חשבון ← נכנסים לאזור האישי. חשבון חדש נוצר אוטומטית, בלי סיסמה.

---

## 4. אחרי שכבר יש כתובת סופית

כל שינוי כתובת (למשל מעבר לדומיין משלך) מחייב לעדכן **שלושה מקומות**:
1. `PUBLIC_BASE_URL` ב-Render
2. **Authorized JavaScript origins** ו-**redirect URIs** ב-Google
3. `PUBLIC_BASE_URL` ב-GitHub (שלב 7)

---

## 5. מיילים: אימות, התראות ופניות למגייסים

בלי SMTP המיילים לא יוצאים, ולכן משתמשים שנרשמו עם סיסמה לא יכולים לאמת את הכתובת.
הדרך הפשוטה היא Gmail:
1. בחשבון Google: **Security** ← להפעיל **2-Step Verification**.
2. https://myaccount.google.com/apppasswords ← שם `job-monitor` ← **Create** ← מעתיקים את הסיסמה (16 אותיות).
3. ב-Render (וגם ב-GitHub בשלב 7):
   `SMTP_HOST=smtp.gmail.com`, `SMTP_USER=<המייל>`, `SMTP_PASSWORD=<סיסמת האפליקציה>`, `SMTP_FROM=<המייל>`

### 5א. פניות מה-Gmail של המשתמשת + "נפתח ✓✓" (לא חובה)

כשמשתמשת מחברת את ה-Gmail שלה, הפניות למגייסים יוצאות מהכתובת שלה, והאתר מראה מתי המגייסת פתחה את המייל.
באותו OAuth client משלב 3:
1. **APIs & Services** ← **Library** ← `Gmail API` ← **Enable**.
2. **Credentials** ← ה-client ← **Authorized redirect URIs** ← להוסיף:
   - `https://<הכתובת שלך>/api/gmail/callback`
   - `http://localhost:8000/api/gmail/callback`
3. **Data Access** (או **Scopes**) ← **Add or remove scopes** ← לסמן `.../auth/gmail.send` ← **Update** ← **Save**.
4. `GMAIL_TOKEN_KEY` נוצר אוטומטית ב-Render (ב-`render.yaml`). **לא לשנות אותו:** שינוי ינתק את כל החיבורים, וכל משתמשת תצטרך לחבר מחדש.
   לפיתוח מקומי: להוסיף ל-`.env` מחרוזת אקראית של 32 תווים ומעלה.

**חשוב לדעת:** `gmail.send` היא הרשאה "רגישה" אצל Google.
- **לפני אימות של Google:** עד 100 משתמשים, שיש להוסיף ידנית ב-**Audience** ← **Test users**. הם יראו אזהרה "Google hasn't verified this app", והחיבור שלהם פג אחרי **7 ימים** (אז מחברים מחדש).
- **לפתיחה לכולם:** **Audience** ← **Publish app** ← Google יבקש אימות: מדיניות פרטיות (כבר קיימת ב-`/privacy`), הסבר למה צריך את ההרשאה, וסרטון קצר שמראה את השימוש. התהליך לוקח בדרך כלל כמה ימים עד כמה שבועות.
- הכניסה הרגילה עם Google (שלב 3) לא מושפעת. היא משתמשת רק בהרשאות בסיסיות.

---

## 6. Google Search Console: כדי שהאתר יופיע בחיפוש

מה כבר מוכן באתר:
- כותרת ותיאור לכל עמוד ציבורי, כתובת canonical ותגיות Open Graph.
- `/robots.txt`: פתוח לכל העמודים הציבוריים, וחוסם את האזור האישי, המשרות, הניהול וה-API.
- `/sitemap.xml`: דף הבית, כניסה, פרטיות ותנאי שימוש.
- עמודים פרטיים מסומנים `noindex`, וכתובת שלא קיימת מחזירה 404 אמיתי.

מה לעשות:
1. https://search.google.com/search-console ← **Add property** ← **URL prefix** ← `https://job-monitor-ab12.onrender.com/`
2. שיטת אימות **HTML tag**: מעתיקים רק את הערך של `content="..."`.
3. ב-Render: `GOOGLE_SITE_VERIFICATION=<הערך>` ← **Save Changes** ← מחכים שהפריסה תסתיים ← ב-Search Console לוחצים **Verify**.
4. **Sitemaps** ← `sitemap.xml` ← **Submit**.
5. **URL inspection** ← כתובת דף הבית ← **Request indexing**.

הופעה ראשונה בתוצאות החיפוש לוקחת בדרך כלל כמה ימים עד שבועות.

---

## 7. הסריקה היומית: GitHub Actions

במאגר ב-GitHub: **Settings** ← **Secrets and variables** ← **Actions**:
- לשונית **Secrets** ← **New repository secret**:
  `DATABASE_URL` (אותו connection string של Neon), ואם הוגדר גם `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD` ו-`SMTP_FROM`
- לשונית **Variables** ← **New repository variable**: `PUBLIC_BASE_URL` = הכתובת של האתר (בשביל הקישורים במיילים)

בדיקה: **Actions** ← **Job Monitor** ← **Run workflow**. אחרי כ-5 דקות, עמוד "ריצות" באתר מציג את הריצה.
מכאן הסריקה רצה כל יום ב-07:00 שעון ישראל.

> אם אחד האתרים חוסם שרתים מחוץ לישראל, זה יופיע כשגיאה בעמוד "מקורות". במקרה כזה אפשר להריץ את הסריקה מהמחשב המקומי מול אותו בסיס נתונים:
> `set DATABASE_URL=<Neon>` ואז `.venv\Scripts\python -m backend.cli run`

---

## 8. דומיין משלך (לא חובה)

1. קונים דומיין (Namecheap, Cloudflare, GoDaddy, או דומיין `.co.il` אצל רשם ישראלי).
2. ב-Render ← השירות ← **Settings** ← **Custom Domains** ← **Add**, למשל `www.example.co.il` וגם `example.co.il`.
3. אצל הרשם מגדירים את רשומות ה-DNS ש-Render מציג (בדרך כלל `CNAME` של `www` אל `job-monitor-ab12.onrender.com`, ורשומת `A` או `ALIAS` לדומיין עצמו). תעודת HTTPS מונפקת אוטומטית.
4. מעדכנים את הכתובת בשלושת המקומות מסעיף 4, ומוסיפים property חדש ב-Search Console.

---

## 9. בדיקת סיום

- [ ] הכתובת הציבורית נפתחת ממכשיר אחר (למשל טלפון על רשת סלולרית)
- [ ] "המשך עם Google" ← החשבון נוצר ← האזור האישי נפתח
- [ ] רענון העמוד (F5): עדיין מחובר/ת
- [ ] "יציאה" ← חזרה לדף הבית ← כניסה שוב עם Google ← אותו חשבון
- [ ] הרשמה עם אימייל וסיסמה ← מייל אימות מגיע ← הקישור מאמת
- [ ] החשבון `ADMIN_EMAILS` רואה את לשונית "ניהול"
- [ ] `<כתובת>/robots.txt` ו-`<כתובת>/sitemap.xml` נפתחים
- [ ] ריצה ידנית ב-GitHub Actions מופיעה בעמוד "ריצות"
