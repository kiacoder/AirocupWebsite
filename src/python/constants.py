"containing various constants used throughout the airocup application"

import os
from typing import Dict, Optional, Tuple
from better_profanity import profanity  # type:ignore
import jdatetime  # type:ignore


class Path:
    "Define all Paths Of Files"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(base_dir, "..", ".."))
    static_dir = os.path.join(root_dir, "static")
    css_dir = os.path.join(static_dir, "css")
    js_dir = os.path.join(static_dir, "js")
    templates_dir = os.path.join(root_dir, "src", "templates")
    admin_templates_dir = os.path.join(templates_dir, "admin")
    client_templates_dir = os.path.join(templates_dir, "client")
    global_templates_dir = os.path.join(templates_dir, "global")
    uploads_dir = os.path.join(static_dir, "uploads")
    images_dir = os.path.join(static_dir, "images")
    receipts_dir = os.path.join(uploads_dir, "receipts")
    news_dir = os.path.join(uploads_dir, "news")
    news_html_dir = os.path.join(static_dir, "news", "htmls")
    gallery_dir = os.path.join(images_dir, "gallery")
    committee_dir = os.path.join(images_dir, "committee")
    technical_committee_dir = os.path.join(images_dir, "technical_committee")
    database_dir = os.path.join(static_dir, "database")
    database = os.path.join(database_dir, "airocup.db")
    guideline_dir = os.path.join(database_dir, "guideline")
    guideline_file = os.path.join(guideline_dir, "guideline.pdf")
    css_style = "css/style.css"
    js_main = "js/main.js"
    logo = "images/logo/"
    gallery = "images/gallery/"
    committee = "images/committee/"
    technical_committee = "images/technical_committee/"
    sponsors = "images/logo/sponsors/"
    poster = "images/poster/poster.png"
    guideline = "database/guideline/guideline.pdf"
    site_web_manifest = "site.webmanifest"
    solid_logos = {
        "main_fest_192": "images/logo/solid/png/192-BWT.png",
        "main_fest_512": "images/logo/solid/png/512-BWT.png",
        "solid_purple_glow_crop": "images/logo/solid/png/BWT.png",
        "solid_purple_glow": "images/logo/solid/png/BWT.png",
        "solid_white": "images/logo/solid/png/BWT.png",
        "solid_white_favicon": "images/logo/solid/ico/BWT.ico",
    }
    transparent_logos = {
        "transparent_black": "images/logo/transparent/tb_airocup_logo.png",
        "transparent_purple": "images/logo/transparent/tp_airocup_logo.png",
        "transparent_white": "images/logo/transparent/tw_airocup_logo.png",
        "favicon": "images/logo/transparent/favicon.svg",
    }

    sponsors_logos = {
        "education_ministry": "images/logo/sponsors/amoozsh_parvarsh.png",
        "interior_ministry": (
            "images/logo/sponsors/ministry_of_the_interior_of_iran.png"
        ),
        "student_research_center": ("images/logo/sponsors/student_research_center.png"),
        "student_research_center_tehran": (
            "images/logo/sponsors/student_research_center.png"
        ),
        "science_ministry": (
            "images/logo/sponsors/ministry_of_science_and_technology.png"
        ),
        "education_department_tehran": (
            "images/logo/sponsors/education_department_tehran.png"
        ),
        "university": "images/logo/sponsors/university_logo.png",
        "water_waste": "images/logo/sponsors/water_and_waste.png",
    }


provinces_data = {
    "آذربایجان شرقی": [
        "آبش‌احمد",
        "آذرشهر",
        "آقکند",
        "اسکو",
        "اهر",
        "ایلخچی",
        "باسمنج",
        "بخشایش",
        "بستان‌آباد",
        "بناب",
        "ترک",
        "ترکمانچای",
        "تسوج",
        "تیکمه‌داش",
        "جلفا",
        "خاروانا",
        "خامنه",
        "خمارلو",
        "خواجه",
        "دوزدوزان",
        "زرنق",
        "زنوز",
        "سراب",
        "سردرود",
        "سیس",
        "شبستر",
        "شربیان",
        "شرفخانه",
        "شندآباد",
        "صوفیان",
        "عجب‌شیر",
        "قره‌آغاج",
        "کشکسرای",
        "کلوانق",
        "کلیبر",
        "کندوان",
        "گوگان",
        "لیلان",
        "مراغه",
        "مرند",
        "ملکان",
        "ممقان",
        "میانه",
        "نظرکهریزی",
        "هادی‌شهر",
        "هریس",
        "هوراند",
        "ورزقان",
        "یامچی",
        "تبریز",
    ],
    "آذربایجان غربی": [
        "ارومیه",
        "اشنویه",
        "ایواوغلی",
        "باروق",
        "بازرگان",
        "بوکان",
        "پلدشت",
        "پیرانشهر",
        "تکاب",
        "چهاربرج",
        "خوی",
        "دیزج‌دیز",
        "ربط",
        "زرآباد",
        "سرو",
        "سلماس",
        "سیه‌چشمه",
        "سیمینه",
        "شاهین‌دژ",
        "شوط",
        "فیرورق",
        "قره‌ضیاءالدین",
        "قوشچی",
        "کشاورز",
        "ماکو",
        "محمدیار",
        "محمودآباد",
        "مرگنلر",
        "مهاباد",
        "میاندوآب",
        "نالوس",
        "نقده",
    ],
    "اردبیل": [
        "اردبیل",
        "اصلاندوز",
        "بیله‌سوار",
        "پارس‌آباد",
        "تازه‌کندانگوت",
        "جعفرآباد",
        "خلخال",
        "سرعین",
        "فخرآباد",
        "کلور",
        "کوراییم",
        "گرمی",
        "گیوی",
        "لاهرود",
        "مرادلو",
        "مشگین‌شهر",
        "نمین",
        "نیر",
        "هشتجین",
    ],
    "اصفهان": [
        "اصفهان",
        "آران و بیدگل",
        "ابریشم",
        "ابوزیدآباد",
        "اردستان",
        "اژیه",
        "بادرود",
        "برزک",
        "بهاران‌شهر",
        "بوئین و میاندشت",
        "تودشک",
        "تیران",
        "جندق",
        "جوزدان",
        "چادگان",
        "چرمهین",
        "حبیب‌آباد",
        "حسن‌آباد",
        "خالدآباد",
        "خمینی‌شهر",
        "خوانسار",
        "خور",
        "داران",
        "دهق",
        "دهاقان",
        "درچه",
        "رزوه",
        "رضوان‌شهر",
        "زازران",
        "زرین‌شهر",
        "زیار",
        "سده لنجان",
        "سمیرم",
        "شاهین‌شهر",
        "شهرضا",
        "طالخونچه",
        "عسگران",
        "علویجه",
        "فرخی",
        "فریدون‌شهر",
        "فلاورجان",
        "فولادشهر",
        "قهدریجان",
        "کاشان",
        "کامو و چوگان",
        "کمشچه",
        "کهریزسنگ",
        "گلپایگان",
        "گلدشت",
        "گلشهر",
        "گوگد",
        "محمدآباد",
        "مهاباد",
        "میمه",
        "نائین",
        "نجف‌آباد",
        "نصرآباد",
        "نطنز",
        "نیاسر",
        "نیک‌آباد",
        "هرند",
    ],
    "البرز": [
        "کرج",
        "اشتهارد",
        "تنکمان",
        "چهارباغ",
        "هشتگرد",
        "طالقان",
        "فردیس",
        "کمال‌شهر",
        "گرمدره",
        "گلسار",
        "ماهدشت",
        "محمدشهر",
        "مشکین‌دشت",
        "نظرآباد",
    ],
    "ایلام": [
        "ایلام",
        "آبدانان",
        "آسمان‌آباد",
        "ارکواز",
        "ایوان",
        "بدره",
        "پهله",
        "توحید",
        "چوار",
        "دره‌شهر",
        "دهلران",
        "زرنه",
        "سرابله",
        "لومار",
        "ماژین",
        "مورموری",
        "مهران",
    ],
    "بوشهر": [
        "بوشهر",
        "آب‌پخش",
        "اهرم",
        "انارستان",
        "بادوله",
        "بردخون",
        "بردستان",
        "برازجان",
        "بندردیر",
        "بندردیلم",
        "بندرریگ",
        "بندرکنگان",
        "بندرگناوه",
        "تنگ ارم",
        "جم",
        "چغادک",
        "خارک",
        "خورموج",
        "دالکی",
        "دلوار",
        "ریز",
        "سعدآباد",
        "شنبه",
        "عسلویه",
        "کاکی",
        "کلمه",
        "نخل‌تقی",
        "وحدتیه",
    ],
    "تهران": [
        "آبسرد",
        "آبعلی",
        "احمدآباد مستوفی",
        "اسلام‌شهر",
        "اندیشه",
        "باغستان",
        "باقرشهر",
        "بومهن",
        "پاکدشت",
        "پردیس",
        "پیشوا",
        "تجریش",
        "تهران",
        "جوادآباد",
        "چهاردانگه",
        "حسن‌آباد",
        "دماوند",
        "رباط‌کریم",
        "رودهن",
        "ری",
        "شاهدشهر",
        "شریف‌آباد",
        "شمشک",
        "شهرقدس",
        "شهرری",
        "شهریار",
        "صالح‌آباد",
        "صباشهر",
        "صفادشت",
        "فردوسیه",
        "فشم",
        "فیروزکوه",
        "قدس",
        "قرچک",
        "کهریزک",
        "گلستان",
        "لواسان",
        "ملارد",
        "نسیم‌شهر",
        "نصیرآباد",
        "ورامین",
    ],
    "چهارمحال و بختیاری": [
        "اردل",
        "آلونی",
        "باباحیدر",
        "بروجن",
        "بلداجی",
        "بن",
        "جونقان",
        "دستنا",
        "سرخون",
        "سردشت",
        "سودجان",
        "شلمزار",
        "شهرکرد",
        "فارسان",
        "فرادبنه",
        "فرخ‌شهر",
        "کاج",
        "کیان",
        "گندمان",
        "گهرو",
        "مال‌خلیفه",
        "ناغان",
        "نافچ",
        "نقنه",
        "وردنجان",
        "هفشجان",
    ],
    "خراسان جنوبی": [
        "آیسک",
        "ارسک",
        "اسدیه",
        "اسفدن",
        "بشرویه",
        "بیرجند",
        "خضری‌دشت‌بیاض",
        "خوسف",
        "زهان",
        "سرایان",
        "سربیشه",
        "سه‌قلعه",
        "طبس",
        "فردوس",
        "قاین",
        "محمدشهر",
        "مود",
        "نهبندان",
    ],
    "خراسان رضوی": [
        "مشهد",
        "نیشابور",
        "سبزوار",
        "تربت حیدریه",
        "کاشمر",
        "قوچان",
        "تربت جام",
        "تایباد",
        "چناران",
        "سرخس",
        "فریمان",
        "بردسکن",
        "گناباد",
        "درگز",
        "خواف",
        "رشتخوار",
        "فیض‌آباد",
        "سلامی",
        "شاندیز",
        "طرقبه",
        "کلات",
        "سنگان",
    ],
    "خراسان شمالی": [
        "بجنورد",
        "شیروان",
        "اسفراین",
        "جاجرم",
        "فاروج",
        "گرمه",
        "آشخانه",
        "راز",
        "سنخواست",
        "شوقان",
        "لوجلی",
        "پیش قلعه",
        "حصارگرمخان",
        "درق",
        "ساروج",
        "قاضی",
    ],
    "خوزستان": [
        "اهواز",
        "آبادان",
        "آغاجاری",
        "اندیکا",
        "اندیمشک",
        "ایذه",
        "باغ‌ملک",
        "بهبهان",
        "ماهشهر",
        "رامشیر",
        "رامهرمز",
        "خرمشهر",
        "دزفول",
        "شادگان",
        "شادمان",
        "شوش",
        "شوشتر",
        "کارون",
        "مسجدسلیمان",
        "هویزه",
        "هفتگل",
        "لالی",
    ],
    "زنجان": [
        "زنجان",
        "ابهر",
        "خرمدره",
        "قیدار",
        "هیدج",
        "صائین‌قلعه",
        "آب‌بر",
        "سلطانیه",
        "ماهنشان",
        "زرین‌رود",
        "چورزق",
        "دندی",
        "سجاس",
        "کرسف",
        "نیک‌پی",
        "حلب",
        "ارمغانخانه",
    ],
    "سمنان": [
        "سمنان",
        "شاهرود",
        "دامغان",
        "گرمسار",
        "مهدی‌شهر",
        "ایوانکی",
        "شهمیرزاد",
        "آرادان",
        "بیارجمند",
        "دیباج",
        "رودیان",
        "سرخه",
        "کلاته",
        "کهن‌آباد",
        "مجن",
        "مهمانسرا",
    ],
    "سیستان و بلوچستان": [
        "زاهدان",
        "زابل",
        "ایرانشهر",
        "چابهار",
        "سراوان",
        "خاش",
        "کنارک",
        "جالق",
        "سرباز",
        "نیک‌شهر",
        "میرجاوه",
        "بمپور",
        "پیشین",
        "راسک",
        "سوران",
        "فنوج",
        "قصرقند",
        "محمدان",
        "هیدوج",
    ],
    "فارس": [
        "شیراز",
        "کازرون",
        "جهرم",
        "مرودشت",
        "فسا",
        "داراب",
        "لار",
        "آباده",
        "نورآباد",
        "اقلید",
        "استهبان",
        "بوانات",
        "خرامه",
        "خنج",
        "سپیدان",
        "فراشبند",
        "قیر و کارزین",
        "کوار",
        "گراش",
        "ممسنی",
        "نی‌ریز",
        "ارژن",
        "ایج",
        "بابانار",
        "حاجی‌آباد",
        "زرقان",
        "سروستان",
        "شهرصدرا",
        "صفاشهر",
        "کره‌ای",
        "مهر",
    ],
    "قزوین": [
        "قزوین",
        "تاکستان",
        "الوند",
        "آبیک",
        "اقبالیه",
        "محمودآباد نمونه",
        "محمدیه",
        "بویین‌زهرا",
        "اسفرورین",
        "ارداق",
        "شال",
        "ضیاءآباد",
        "خرمدشت",
        "سگزآباد",
        "نرجه",
        "کوهین",
    ],
    "قم": [
        "قم",
        "جعفریه",
        "کهک",
        "قنوات",
        "سلفچگان",
        "دستجرد",
        "سعدآباد",
        "نوفل‌لوشاتو",
        "قاهان",
        "کرجندان",
    ],
    "کردستان": [
        "سنندج",
        "سقز",
        "مریوان",
        "بانه",
        "کامیاران",
        "قروه",
        "دیواندره",
        "بیجار",
        "دهگلان",
        "سروآباد",
        "یاسوکند",
        "بلبان‌آباد",
        "موچش",
        "آرمرده",
        "دلبران",
        "سریش‌آباد",
        "زرینه",
    ],
    "کرمان": [
        "کرمان",
        "سیرجان",
        "رفسنجان",
        "جیرفت",
        "بم",
        "زرند",
        "کهنوج",
        "شهر بابک",
        "انار",
        "بافت",
        "بردسیر",
        "رابر",
        "راور",
        "ریگان",
        "منوجان",
        "نرماشیر",
        "فهرج",
        "قلعه‌گنج",
        "کوهبنان",
        "گلباف",
        "ماهان",
        "پاریز",
        "چترود",
        "خانوک",
        "درب بهشت",
        "زیدآباد",
        "نگار",
    ],
    "کرمانشاه": [
        "کرمانشاه",
        "اسلام‌آباد غرب",
        "هرسین",
        "کنگاور",
        "جوانرود",
        "سنقر",
        "پاوه",
        "صحنه",
        "روانسر",
        "ثلاث باباجانی",
        "دالاهو",
        "سرپل ذهاب",
        "قصر شیرین",
        "گیلانغرب",
        "نودشه",
        "نوسود",
        "ازگله",
        "باینگان",
        "تازه‌آباد",
    ],
    "کهگیلویه و بویراحمد": [
        "یاسوج",
        "دوگنبدان",
        "دهدشت",
        "لیکک",
        "چرام",
        "لنده",
        "باشت",
        "پاتاوه",
        "چیتاب",
        "سوق",
        "گراب سفلی",
        "مادوان",
        "مارگون",
    ],
    "گلستان": [
        "گرگان",
        "گنبد کاووس",
        "علی‌آباد کتول",
        "ترکمن",
        "آق‌قلا",
        "کردکوی",
        "بندر گز",
        "مینودشت",
        "آزادشهر",
        "رامیان",
        "کلاله",
        "گالیکش",
        "مراوه‌تپه",
        "نوکنده",
    ],
    "گیلان": [
        "رشت",
        "انزلی",
        "لاهیجان",
        "لنگرود",
        "آستارا",
        "صومعه‌سرا",
        "رودسر",
        "فومن",
        "ماسال",
        "آستانه اشرفیه",
        "رودبار",
        "شفت",
        "سیاهکل",
        "اطاقور",
        "اسالم",
        "کیاشهر",
        "پره سر",
        "چابکسر",
        "حویق",
        "خشکبیجار",
        "رضوانشهر",
        "سنگر",
        "شلمان",
        "کومله",
        "لشت نشا",
        "لولمان",
        "مرجقل",
    ],
    "لرستان": [
        "خرم‌آباد",
        "بروجرد",
        "دورود",
        "کوهدشت",
        "الیگودرز",
        "نورآباد",
        "ازنا",
        "الشتر",
        "پلدختر",
        "سپیددشت",
        "معمولان",
        "مومن‌آباد",
        "ویسیان",
        "چغلوندی",
        "چقابل",
        "زاغه",
        "سراب دوره",
        "فیروزآباد",
        "کوهنانی",
        "هفت‌چشمه",
    ],
    "مازندران": [
        "ساری",
        "بابل",
        "آمل",
        "قائم‌شهر",
        "بهشهر",
        "چالوس",
        "نکا",
        "بابلسر",
        "نوشهر",
        "رامسر",
        "تنکابن",
        "عباس‌آباد",
        "فریدون‌کنار",
        "کلاردشت",
        "سوادکوه",
        "محمودآباد",
        "میاندورود",
        "پل سفید",
        "جویبار",
        "نور",
        "گلوگاه",
    ],
    "مرکزی": [
        "اراک",
        "ساوه",
        "خمین",
        "محلات",
        "دلیجان",
        "تفرش",
        "آشتیان",
        "شازند",
        "زرندیه",
        "فراهان",
        "کمیجان",
        "خنداب",
        "مامونیه",
        "نوبران",
        "نیمور",
        "هندودر",
        "آوه",
        "پرندک",
        "جاورسیان",
        "خسروبیک",
        "داودآباد",
        "سنجان",
        "غرق‌آباد",
        "کارچان",
    ],
    "هرمزگان": [
        "بندرعباس",
        "میناب",
        "دهبارز",
        "لنگه",
        "قشم",
        "کیش",
        "حاجی‌آباد",
        "بستک",
        "جاسک",
        "خمیر",
        "رودان",
        "سیریک",
        "فین",
        "گاوبندی",
        "پارسیان",
        "تخت",
        "جناح",
        "درگهان",
        "سوزا",
        "کوهستک",
        "لمزان",
        "هشتبندی",
    ],
    "همدان": [
        "همدان",
        "ملایر",
        "نهاوند",
        "تویسرکان",
        "اسدآباد",
        "کبودرآهنگ",
        "بهار",
        "رزن",
        "فامنین",
        "قروه درجزین",
        "آجین",
        "برزول",
        "جورقان",
        "دمق",
        "شراء",
        "صالح‌آباد",
        "فرسفج",
        "قلقلرود",
        "گیان",
    ],
    "یزد": [
        "یزد",
        "میبد",
        "اردکان",
        "بافق",
        "مهریز",
        "ابرکوه",
        "تفت",
        "هرات",
        "اشکذر",
        "بهاباد",
        "حمیدیا",
        "زارچ",
        "شاهدیه",
        "عقدا",
        "مروست",
        "ندوشن",
        "نیر",
    ],
}

leagues_list = [
    {
        "id": 1,
        "name": "لیگ آیروچلنج حل چالش‌ها با ربات و هوش مصنوعی",
        "icon": "fa-puzzle-piece",
        "description": (
            "لیگ آیروچلنج، نقطه‌ی تلاقی خلاقیت، مهارت فنی و تفکر حل‌مسئله است. "
            "در این رقابت، شرکت‌کنندگان با طراحی ربات‌ها یا الگوریتم‌های هوشمند، "
            "مأموریت‌های واقعی را در زمینه‌های گوناگون مانند نجات، حمل‌ونقل یا "
            "محیط‌زیست حل می‌کنند. این لیگ ترکیبی از نوآوری مهندسی و هوش مصنوعی "
            "است و بستری برای سنجش توانایی تیم‌ها در طراحی، پیاده‌سازی و تحلیل "
            "سیستم‌های هوشمند فراهم می‌آورد."
        ),
    },
    {
        "id": 2,
        "name": "لیگ تولید محتوای دیجیتال ویژه بازار کار",
        "icon": "fa-solid fa-compass-drafting",
        "description": (
            "این لیگ با هدف پرورش خلاقیت دیجیتال و مهارت‌های تولید محتوای کاربردی "
            "طراحی شده است. شرکت‌کنندگان در سه سطح (ابتدایی، متوسطه و دانشجویی) "
            "با استفاده از ابزارهای حرفه‌ای و هوش مصنوعی، محتوای آموزشی، تبلیغاتی "
            "یا فرهنگی تولید می‌کنند. داوری بر اساس خلاقیت، کیفیت فنی، تلفیق AI و "
            "کاربردی بودن آثار انجام می‌شود. هدف نهایی، آماده‌سازی نسل جوان برای حضور "
            "مؤثر در بازار کار دیجیتال است."
        ),
    },
    {
        "id": 3,
        "name": "لیگ تولید محتوا با هوش مصنوعی",
        "icon": "fa-solid fa-video",
        "description": (
            "در این لیگ، تمرکز بر تولید ویدئو یا پوسترهای خلاقانه با بهره‌گیری از "
            "ابزارهای هوش مصنوعی است. شرکت‌کنندگان می‌توانند در دو بخش مستقل رقابت "
            "دهند: تولید محتوای ویدیویی و طراحی پوستر تبلیغاتی. این رقابت بستری است "
            "برای نمایش قدرت خلاقیت، مهارت فنی و درک هنری در استفاده از فناوری‌های "
            "مولد (Generative AI) برای انتقال پیام‌های آموزشی، فرهنگی یا تجاری."
        ),
    },
    {
        "id": 4,
        "name": "لیگ ساخت عامل هوشمند (AI Agent)",
        "icon": "fa-brain",
        "description": (
            "در این لیگ، شرکت‌کنندگان به طراحی و توسعه‌ی عامل‌های هوشمند می‌پردازند؛ "
            "سیستم‌هایی که می‌توانند به‌صورت خودکار تصمیم بگیرند، تحلیل کنند و با "
            "کاربر یا محیط تعامل داشته باشند. این عامل‌ها می‌توانند در قالب چت‌بات، "
            "دستیار مجازی یا سیستم‌های تصمیم‌یار طراحی شوند. داوری بر اساس خلاقیت، "
            "کارایی، تعامل کاربری و قابلیت توسعه انجام می‌گیرد."
        ),
    },
    {
        "id": 5,
        "name": "لیگ اختراعات رباتیک و هوش مصنوعی",
        "icon": "fa-lightbulb",
        "description": (
            "این لیگ ترکیبی از پژوهش، نوآوری و کارآفرینی فناورانه است. شرکت‌کنندگان "
            "در سه بخش «محصول»، «ایده» و «پژوهش» رقابت می‌کنند و باید توانایی خود را "
            "در ارائه طرح‌های فناورانه، مدل‌های تجاری‌سازی و مستندات علمی نشان دهند. "
            "هدف اصلی، تبدیل ایده‌های پژوهشی به محصولات واقعی و ایجاد پیوند میان علم، "
            "صنعت و نوآوری است."
        ),
    },
    {
        "id": 6,
        "name": "لیگ جنگجوهای هوشمند",
        "icon": "fa-shield-alt",
        "description": (
            "در این لیگ هیجان‌انگیز، شرکت‌کنندگان ربات‌هایی طراحی می‌کنند که در زمین "
            "مسابقه با رعایت اصول ایمنی با یکدیگر رقابت می‌کنند. هدف اصلی، آموزش اصول "
            "طراحی مکانیکی، کنترل هوشمند و تحلیل استراتژیک است. داوری بر اساس عملکرد، "
            "استراتژی، ایمنی و نوآوری انجام می‌شود. این لیگ برای هر دو سطح دانش‌آموزی "
            "و دانشجویی قابل شرکت است."
        ),
    },
    {
        "id": 7,
        "name": "لیگ برنامه‌نویسی و هوش مصنوعی",
        "icon": "fa-code",
        "description": (
            "این لیگ برای علاقه‌مندان به کدنویسی و حل مسائل پیچیده طراحی شده است. "
            "مسابقه در چهار بخش برگزار می‌شود: اسکرچ، ACM، پایتون و هوش مصنوعی. "
            "شرکت‌کنندگان از مفاهیم پایه تا مباحث پیشرفته الگوریتمی، به رقابت در "
            "بهینه‌سازی کد، دقت و خلاقیت در طراحی راه‌حل می‌پردازند. این لیگ فرصتی "
            "برای شناسایی استعدادهای برتر در حوزه برنامه‌نویسی هوشمند است."
        ),
    },
    {
        "id": 8,
        "name": "لیگ نمایش ربات‌ها",
        "icon": "fa-star",
        "description": (
            "در این لیگ، ربات‌ها نه برای مبارزه بلکه برای نمایش خلاقیت، طراحی و تعامل "
            "با انسان ساخته می‌شوند. تیم‌ها ربات‌هایی را طراحی می‌کنند که بتوانند حرکات "
            "نمایشی، رفتارهای تعاملی یا عملکردهای هنری از خود نشان دهند. ارزیابی بر اساس "
            "نوآوری، جذابیت بصری، کیفیت ارائه و ایمنی انجام می‌شود. این لیگ ترکیبی از "
            "فناوری، هنر و ارتباط با مخاطب است."
        ),
    },
    {
        "id": 9,
        "name": "لیگ ربات امدادگر محیط‌زیست",
        "icon": "fa-leaf",
        "description": (
            "در این رقابت، ربات‌ها مأموریت دارند تا در سناریوهای امدادی و زیست‌محیطی "
            "فعالیت کنند؛ از شناسایی آلودگی تا جمع‌آوری پسماند یا نجات در شرایط بحرانی. "
            "شرکت‌کنندگان باید ربات‌هایی بسازند که بتوانند به‌صورت خودمختار داده‌ها را "
            "تحلیل و بهترین تصمیم را اتخاذ کنند. این لیگ تلفیقی از علم، فناوری و مسئولیت "
            "اجتماعی است."
        ),
    },
    {
        "id": 10,
        "name": "لیگ ربات پرنده",
        "icon": "fa-solid fa-plane",
        "description": (
            "این لیگ برای علاقه‌مندان به طراحی پهپادها و سیستم‌های پروازی هوشمند طراحی "
            "شده است. تیم‌ها باید ربات‌های پرنده‌ای بسازند که توانایی انجام مأموریت‌های "
            "خاص مانند حمل بار، فیلم‌برداری یا نقشه‌برداری خودکار را داشته باشند. ارزیابی "
            "بر اساس پایداری پرواز، دقت کنترل، ایمنی و نوآوری در طراحی انجام می‌شود."
        ),
    },
    {
        "id": 11,
        "name": "لیگ خودرو خودران",
        "icon": "fa-solid fa-car",
        "description": (
            "در این لیگ، شرکت‌کنندگان باید یک خودروی هوشمند طراحی کنند که بتواند در مسیر "
            "مشخص، موانع را شناسایی کرده و به‌صورت خودکار حرکت کند. محورهای اصلی شامل "
            "بینایی ماشین، کنترل خودکار و تصمیم‌گیری هوشمند است. این لیگ مقدمه‌ای برای ورود "
            "به دنیای وسایل نقلیه خودران و فناوری‌های آینده‌ی حمل‌ونقل است."
        ),
    },
    {
        "id": 12,
        "name": "لیگ کشاورز هوشمند (AgriTech AI)",
        "icon": "fa-solid fa-tractor",
        "description": (
            "هدف این لیگ، پرورش مهارت‌های هوش مصنوعی در حوزه‌ی کشاورزی است. شرکت‌کنندگان "
            "با طراحی الگوریتم‌ها و عامل‌های هوشمند در محیط شبیه‌سازی‌شده، به بهینه‌سازی "
            "مصرف آب، کود، بذر و انرژی می‌پردازند. داوری بر اساس دقت تشخیص، بهره‌وری منابع "
            "و عملکرد کلی انجام می‌شود. این رقابت بستری برای توسعه فناوری‌های AgriTech در ایران است"
        ),
    },
    {
        "id": 13,
        "name": "لیگ هوش مصنوعی در علوم پزشکی و سلامت (Medi AI)",
        "icon": "fa-stethoscope",
        "description": (
            "در این لیگ، تیم‌ها راهکارهای مبتنی بر هوش مصنوعی برای تحلیل داده‌های پزشکی، "
            "تشخیص بیماری‌ها، پایش سلامت و تصمیم‌یارهای بالینی توسعه می‌دهند. هدف، آموزش "
            "کاربردهای علمی و اخلاقی هوش مصنوعی در پزشکی است. داوری بر اساس دقت مدل، نوآوری، "
            "قابلیت تفسیر و کاربردپذیری در نظام سلامت انجام می‌شود."
        ),
    },
    {
        "id": 14,
        "name": "لیگ مدیریت هوشمند مصرف آب (Aqua AI)",
        "icon": "fa-tint",
        "description": (
            "با توجه به بحران آب در ایران، این لیگ با هدف آموزش هوش مصنوعی در مدیریت منابع "
            "آبی طراحی شده است. در دو سطح دانش‌آموزی و دانشجویی، شرکت‌کنندگان با داده‌های "
            "واقعی کار کرده و مدل‌هایی برای پیش‌بینی مصرف، تشخیص نشتی و بهینه‌سازی شبکه‌های "
            "آبرسانی طراحی می‌کنند. این لیگ نمونه‌ای از کاربرد مستقیم علم داده و AI در حل "
            "چالش‌های ملی است."
        ),
    },
]


education_levels: Dict[str, Dict[str, Optional[Tuple[Optional[int], Optional[int]]]]] = {
    "ابتدایی": {"grades": (1, 6), "ages": (6, 12)},
    "متوسطه اول": {"grades": (7, 9), "ages": (6, 15)},
    "متوسطه دوم": {"grades": (10, 12), "ages": (6, 18)},
    "دانشجویی": {"grades": None, "ages": (6, 65)},
    "آزاد": {"grades": None, "ages": (19, None)},
}

allowed_education = set(education_levels.keys())

education_age_ranges = {
    level: details["ages"]
    for level, details in education_levels.items()
    if details["ages"]
}

week_days = {
    "saturday": "شنبه",
    "sunday": "یکشنبه",
    "monday": "دوشنبه",
    "tuesday": "سه‌شنبه",
    "wednesday": "چهارشنبه",
    "thursday": "پنجشنبه",
    "friday": "جمعه",
}

technical_committee_members = [
    {
        "name": "دکتر سمیه سلطانی",
        "role": "رئیس لیگ کاربرد هوش مصنوعی در علوم پزشکی و بهداشت",
        "description": "استاد دانشگاه تبریز",
        "image": "images/technical_committee/somaieh_soltani.png",
    },
    {
        "name": "مهندس امیر حسین کرمی",
        "role": "مدیر امور استان ها",
        "description": "هماهنگی٬ برنامه ریزی و پیگیری امور استان ها",
        "image": "images/technical_committee/amir_hossain.png",
    },
]


class ForbiddenContent:
    "Manages the application's profanity filter and custom word list"

    custom_words = {
        "admin",
        "administrator",
        "mod",
        "sex",
        "boobs",
        "penis",
        "moderator",
        "root",
        "spam",
        "free",
        "money",
        "win",
        "idiot",
        "stupid",
        "fool",
        "fuck",
        "airocup",
        "a.i.r.o.c.u.p",
        "آیروکاپ",
        "مدیرکل",
        "ناظر",
        "کارشناس",
        "توسعه‌دهنده",
        "برنامه‌نویس",
        "سرپرست",
        "لیدر",
        "همراه",
        "پشتیبان فنی",
        "ادمین",
        "مدیر",
        "پشتیبان",
        "رایگان",
        "جایزه",
        "برنده",
        "احمق",
        "نادان",
        "ابله",
        "ass",
        "bitch",
        "cock",
        "cunt",
        "dick",
        "nigger",
        "pussy",
        "shit",
        "whore",
        "douchebag",
        "hells",
        "faggot",
        "wanker",
        "bollocks",
        "fucking",
        "dammit",
        "douche",
        "twat",
        "dickhead",
        "fag",
        "bastard",
        "slut",
        "goddamn",
        "damn",
        "bloody",
        "fuckface",
        "crap",
        "shithead",
        "bullshit",
        "dumbass",
        "shitty",
        "hell",
        "fucked",
        "god",
        "motherfucker",
        "retard",
        "nigga",
        "piss",
    }

    filter_loaded = False

    @staticmethod
    def _initialize_filter():
        "Loads the default library list and adds our custom list"
        if not ForbiddenContent.filter_loaded:
            profanity.load_censor_words()
            profanity.add_censor_words(
                [w.lower() for w in ForbiddenContent.custom_words]
            )
            ForbiddenContent.filter_loaded = True

    @staticmethod
    def censor(text: str) -> str:
        "Censors any profane text"
        ForbiddenContent._initialize_filter()
        return profanity.censor(text)

    @staticmethod
    def contains_profanity(text: str) -> bool:
        "Checks if text contains any profane word"
        ForbiddenContent._initialize_filter()
        return profanity.contains_profanity(text)


class Date:
    "Date-related constants and methods for the application"
    persian_months = {
        1: "فروردین",
        2: "اردیبهشت",
        3: "خرداد",
        4: "تیر",
        5: "مرداد",
        6: "شهریور",
        7: "مهر",
        8: "آبان",
        9: "آذر",
        10: "دی",
        11: "بهمن",
        12: "اسفند",
    }

    @staticmethod
    def get_allowed_years():
        "Returns a list of allowed Jalali birth years for participants based on age limits (5-80)."
        today_jalali = jdatetime.date.today()
        min_age = 5
        max_age = 80
        start_year = today_jalali.year - max_age
        end_year = today_jalali.year - min_age
        return list(range(start_year, end_year + 1))


class AppConfig:
    "Configuration constants for the application."
    max_team_per_client = 20
    max_members_per_team = 10
    max_image_size = 50 * 1024 * 1024
    max_office_size = 50 * 1024 * 1024
    max_document_size = 200 * 1024 * 1024
    max_video_size = 200 * 1024 * 1024
    image_extensions = {"png", "jpg", "jpeg", "gif"}
    office_extensions = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx"}
    video_extensions = {"mp4", "mov", "avi", "mkv", "webm"}
    allowed_extensions = sorted(image_extensions | office_extensions | video_extensions)
    allowed_mime_types = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "video/mp4",
        "video/quicktime",
        "video/x-msvideo",
        "video/x-matroska",
        "video/webm",
    ]


class Details:
    "Details for airocup event"
    address = "دانشگاه علم و صنعت ایران، تهران، ایران"
    google_map_url = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3238.3671459295647!2d51.50422711222071!3d35.74177972652958!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3f8e032fd49e3809%3A0x470e49fef97ae303!2sIran%20University%20of%20Science%20and%20Technology%20(IUST)!5e0!3m2!1sen!2snl!4v1762083993443!5m2!1sen!2snl"
    stage_one = "مجازی"
    stage_two = "حضوری، ۲۳ تا ۲۵ بهمن ۱۴۰۴"
    registration_deadline = "مهلت تا ۳۰ آذر"


class Contact:
    "Contact information for airocup"
    phone = "09352117339"
    email_primary = "airocupiran@gmail.com"
    website = "https://airocup.org"
    instagram = "@airo.cup"
    bale = "https://ble.ir/join/8VwzjR1U3f"
    aparat_channel = "https://www.aparat.com/Kia_coder"
    aparat_playlist = "https://www.aparat.com/playlist/22114839"
    linkedin = "https://www.linkedin.com/company/airocup"
    aparat_embed_url = (
        "https://www.aparat.com/video/video/embed/videohash/wtw75xo/vt/frame"
    )
    eitaa = "https://eitaa.com/airocup2025"
    telegram = "https://t.me/airocup"


contact_points_data = [
    {
        "href": f"mailto:{Contact.email_primary}",
        "icon": "fas fa-envelope",
        "label": "ایمیل اصلی (سازمانی)",
        "display": Contact.email_primary,
        "target": None,
    },
    {
        "href": Contact.bale,
        "icon": "fas fa-comment-dots",
        "label": "کانال بله",
        "display": "@airocup2025",
        "target": "_blank",
    },
    {
        "href": f"https://instagram.com/{Contact.instagram.replace('@', '')}",
        "icon": "fab fa-instagram",
        "label": "اینستاگرام",
        "display": Contact.instagram,
        "target": "_blank",
    },
    {
        "href": Contact.aparat_playlist,
        "icon": "fas fa-play-circle",
        "label": "آپارات",
        "display": "کانال آپارات آیروکاپ",
        "target": "_blank",
    },
    {
        "href": Contact.linkedin,
        "icon": "fa-brands fa-linkedin",
        "label": "لینکدین",
        "display": "کانال لینکدین",
        "target": "_blank",
    },
    {
        "href": Contact.eitaa,
        "icon": "fa-solid fa-users",
        "label": "ایتا",
        "display": "کانال ایتا",
        "target": "_blank",
    },
    {
        "href": Contact.telegram,
        "icon": "fa-brands fa-telegram",
        "label": "تلگرام",
        "display": "کانال تلگرام",
        "target": "_blank",
    },
    {
        "href": f"tel:{Contact.phone}",
        "icon": "fas fa-phone-alt",
        "label": "پشتیبانی",
        "display": Contact.phone,
        "target": None,
    },
]

cooperation_opportunities_data = [
    {
        "icon": "fas fa-handshake",
        "title": "حمایت و اسپانسرشیپ",
        "description": (
            "نام تجاری خود را در قلب بزرگترین رویداد هوش مصنوعی کشور به "
            "نمایش بگذارید و تعهد سازمان خود به نوآوری و پیشرفت فناوری را "
            "نشان دهید."
        ),
    },
    {
        "icon": "fas fa-brain",
        "title": "تعریف چالش‌های صنعتی",
        "description": (
            "مسائل واقعی صنعت خود را از طریق نوآوری باز حل کنید. چالش‌های "
            "سازمان خود را به یک رقابت هیجان‌انگیز برای صدها تیم خلاق تبدیل "
            "کنید."
        ),
    },
    {
        "icon": "fas fa-chalkboard-teacher",
        "title": "همکاری علمی و داوری",
        "description": (
            "دانش و تجربه خود را با نسل آینده به اشتراک بگذارید. از اساتید و "
            "متخصصان برجسته برای ارتقای سطح علمی رویداد دعوت به همکاری "
            "می‌کنیم."
        ),
    },
    {
        "icon": "fas fa-users-cog",
        "title": "پیوستن به تیم اجرایی",
        "description": (
            "اگر فردی پرانرژی و علاقه‌مند به دنیای فناوری هستید، به تیم "
            "اجرایی آیروکاپ بپیوندید و تجربه‌ای بی‌نظیر در برگزاری یک رویداد "
            "ملی کسب کنید."
        ),
    },
    {
        "icon": "fas fa-trophy",
        "title": "برگزاری لیگ‌های تخصصی",
        "description": (
            "تخصص و حوزه فعالیت خود را به یک لیگ رقابتی تبدیل کنید. ما بستر "
            "لازم برای افزودن رقابت‌های جدید به آیروکاپ را فراهم می‌کنیم."
        ),
    },
    {
        "icon": "fas fa-box-open",
        "title": "همکاری در تامین تجهیزات",
        "description": (
            "آیروکاپ به قطعات الکترونیکی، رباتیک و نرم‌افزار نیاز دارد. "
            "از شرکت‌های واردکننده و تامین‌کننده دعوت می‌شود تا با ارائه محصولات "
            "خود، به عنوان شریک فنی در کنار ما باشند."
        ),
    },
    {
        "icon": "fas fa-bullhorn",
        "title": "همکاری رسانه‌ای و تبلیغاتی",
        "description": (
            "از رسانه‌ها، خبرگزاری‌ها و شرکت‌های تبلیغاتی دعوت می‌کنیم تا با "
            "پوشش خبری و اطلاع‌رسانی، به دیده‌شدن این رویداد ملی کمک کرده و "
            "برند خود را معرفی کنند."
        ),
    },
    {
        "icon": "fas fa-university",
        "title": "مشارکت علمی و دانشگاهی",
        "description": (
            "از دانشگاه‌ها، مراکز پژوهشی و موسسات آموزشی دعوت می‌شود تا به عنوان "
            "شرکت علمی، در غنی‌سازی محتوای رویداد و تشویق دانشجویان به شرکت، با "
            "ما همراه شوند."
        ),
    },
    {
        "icon": "fas fa-concierge-bell",
        "title": "ارائه خدمات و پشتیبانی",
        "description": (
            "برگزاری یک رویداد بزرگ نیازمند خدمات اجرایی و پشتیبانی است. از "
            "ارائه‌دهندگان خدمات (لجستیک، پذیرایی و...) برای همکاری در اجرای هرچه "
            "بهتر مسابقات دعوت می‌کنیم."
        ),
    },
]


committee_members_data = [
    {
        "name": "دکتر بهروز مینایی بیدگلی",
        "role": "رئیس مسابقات",
        "description": "رهبری کلی مسابقات و نظارت بر اجرای صحیح تمامی مراحل برگزاری",
        "image": "images/committee/minayi.png",
    },
    {
        "name": "دکتر داوود زارع",
        "role": "رئیس کمیته ملی مسابقات",
        "description": "هماهنگی و نظارت بر کلیه فعالیت‌های کمیته‌های تخصصی",
        "image": "images/committee/davood.png",
    },
    {
        "name": "مهندس زهرا سعادتی داریان",
        "role": "دبیر کمیته علمی",
        "description": "مسئولیت ارزیابی علمی پروژه‌ها و تنظیم معیارهای داوری",
        "image": "images/committee/saadati.png",
    },
    {
        "name": "مهندس محمدرضا ریاحی سامانی",
        "role": "دبیر کمیته رباتیک",
        "description": "مسئولیت برگزاری لیگ‌های رباتیک و ارزیابی ربات‌ها",
        "image": "images/committee/riyahi.png",
    },
    {
        "name": "مهندس پوریا حداد",
        "role": "دبیر کمیته هوش مصنوعی",
        "description": "مسئولیت برگزاری لیگ‌های هوش مصنوعی و ارزیابی پروژه‌ها",
        "image": "images/committee/Poria.png",
    },
    {
        "name": "دکتر محمد خلیل پور",
        "role": "دبیر کمیته پشتیبانی",
        "description": "مسئولیت پشتیبانی فنی و حل مشکلات شرکت‌کنندگان",
        "image": "images/committee/khalil_pore.png",
    },
]

homepage_sponsors_data = [
    {"logo_key": "interior_ministry", "alt_text": "وزارت کشور جمهوری اسلامی ایران"},
    {"logo_key": "science_ministry", "alt_text": "وزارت علوم، تحقیقات و فناوری"},
    {"logo_key": "education_ministry", "alt_text": "وزارت آموزش و پرورش"},
    {
        "logo_key": "education_department_tehran",
        "alt_text": "اداره کل آموزش و پرورش شهر تهران",
    },
    {"logo_key": "student_research_center", "alt_text": "پژوهش سرای دانش‌آموزی"},
    {
        "logo_key": "student_research_center_tehran",
        "alt_text": "پژوهش سرای دانش‌آموزی تهران",
    },
    {"logo_key": "water_waste", "alt_text": "شرکت مهندسی آب و فاضلاب کشور"},
]

gallery_videos_data = [
    {
        "title": "علام برگزاری اولین دوره مسابقات هوش مصنوعی و رباتیک آیروکاپ",
        "src": ("https://www.aparat.com/video/video/embed/videohash/tgg3hv0/vt/frame"),
    },
    {
        "title": "آیروکاپ | آماده سازی نوجوانان برای دنیای رباتیک",
        "src": ("https://www.aparat.com/video/video/embed/videohash/icpiigb/vt/frame"),
    },
    {
        "title": "آیروکاپ | اهمیت دانش رباتیک و مهارت های نرم برای دانش آموزان",
        "src": ("https://www.aparat.com/video/video/embed/videohash/pyv0uga/vt/frame"),
    },
    {
        "title": "آیروکاپ | مشاغل آینده دار برای نوجوانان",
        "src": ("https://www.aparat.com/video/video/embed/videohash/ket93i2/vt/frame"),
    },
]

global_html_names_data = {
    "about": "global/about.html",
    "base": "global/base.html",
    "committee": "global/committee.html",
    "technical_committee": "global/technical_committee.html",
    "contact": "global/contact.html",
    "cooperate": "global/cooperate.html",
    "gallery": "global/gallery.html",
    "index": "global/index.html",
    "leagues": "global/leagues.html",
    "news": "global/news.html",
    "sponsors": "global/sponsors.html",
    "404": "global/404.html",
    "500": "global/500.html",
    "400": "global/400.html",
    "403": "global/403.html",
    "500_debug": "global/500_debug.html",
    "article": "global/article.html",
}

client_html_names_data = {
    "create_team": "client/create_team.html",
    "dashboard": "client/dashboard.html",
    "forgot_password": "client/forgot_password.html",
    "login": "client/login.html",
    "member_form_fields": "client/member_form_fields.html",
    "members": "client/members.html",
    "payment": "client/payment.html",
    "reset_password": "client/reset_password.html",
    "select_league": "client/select_league.html",
    "sign_up": "client/sign_up.html",
    "resolve_issues": "client/resolve_issues.html",
    "support_chat": "client/support_chat.html",
    "update_team": "client/update_team.html",
    "verify": "client/verify.html",
    "edit_member": "client/edit_member.html",
    "my_history": "client/my_history.html",
}

admin_html_names_data = {
    "admin_chat": "admin/admin_chat.html",
    "admin_chat_list": "admin/admin_chat_list.html",
    "admin_clients_list": "admin/admin_clients_list.html",
    "admin_dashboard": "admin/admin_dashboard.html",
    "admin_edit_news": "admin/admin_edit_news.html",
    "admin_edit_team": "admin/admin_edit_team.html",
    "admin_login": "admin/admin_login.html",
    "admin_manage_client": "admin/admin_manage_client.html",
    "admin_manage_news": "admin/admin_manage_news.html",
    "admin_manage_teams": "admin/admin_manage_teams.html",
    "admin_add_member": "admin/admin_add_member.html",
    "admin_select_chat": "admin/admin_chat_list.html",
    "admin_search": "admin/admin_search.html",
    "admin_logs": "admin/admin_logs.html",
}
