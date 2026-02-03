import os
import feedparser
import smtplib
from urllib.parse import quote_plus
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4


# ===============================
# CONFIG
# ===============================

HOURS = 24
MAX_PER_COMPANY = 8
PDF_NAME = "LNG_Daily_Newsletter.pdf"


# ===============================
# COMPANY UNIVERSE
# ===============================

COMPANIES = {
    "GTT": {
        "keywords": ["GTT", "Gaztransport", "Technigaz", "Gaztransport & Technigaz"],
        "strict": None
    },
    "Flex LNG": {
        "keywords": ["Flex LNG", "FLNG"],
        "strict": ["Flex LNG", "FLNG"]
    },
    "Capital Clean Energy Carriers Corp.": {
        "keywords": ["Capital Clean Energy Carriers", "Capital Clean Energy Carriers Corp.", "CCEC"],
        "strict": ["Capital Clean Energy Carriers", "CCEC"]
    },
    "Nakilat": {
        "keywords": ["Nakilat", "Qatar Gas Transport", "QGTS"],
        "strict": ["Nakilat", "QGTS"]
    },
    "Hyundai Heavy Industries": {
        "keywords": ["Hyundai Heavy Industries"],
        "strict": ["Hyundai Heavy Industries"]
    },
    "Hanwha Ocean": {
        "keywords": ["Hanwha Ocean", "DSME", "Daewoo Shipbuilding"],
        "strict": ["Hanwha Ocean", "DSME", "Daewoo Shipbuilding"]
    },
    "Samsung Heavy Industries": {
        "keywords": ["Samsung Heavy Industries"],
        "strict": ["Samsung Heavy Industries"]
    },
    "MOL": {
        "keywords": ["Mitsui O.S.K. Lines", "Mitsui O.S.K."],
        "strict": ["Mitsui O.S.K."]
    },
    "NYK": {
        "keywords": ["Nippon Yusen", "Nippon Yusen Kaisha"],
        "strict": ["Nippon Yusen"]
    },
    "Maran Gas": {
        "keywords": ["Maran Gas", "Maran Gas Maritime"],
        "strict": ["Maran Gas"]
    },
    "Seapeak Maritime": {
        "keywords": ["Seapeak Maritime", "Seapeak"],
        "strict": ["Seapeak"]
    },
    "GasLog": {
        "keywords": ["GasLog", "GasLog Partners"],
        "strict": ["GasLog"]
    },
    "Hyundai Samho Heavy Industries": {
        "keywords": ["Hyundai Samho Heavy Industries"],
        "strict": ["Hyundai Samho"]
    },
    "Hudong-Zhonghua": {
        "keywords": ["Hudong-Zhonghua", "Hudong Zhonghua"],
        "strict": ["Hudong-Zhonghua", "Hudong Zhonghua"]
    }
}


# ===============================
# HELPERS
# ===============================

def passes_strict_filter(title, strict_keywords):
    if strict_keywords is None:
        return True
    t = title.lower()
    for sk in strict_keywords:
        if sk.lower() in t:
            return True
    return False


def fetch_google_news(keywords, hours):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles = []

    for kw in keywords:
        kw_encoded = quote_plus(kw)
        rss_url = (
            "https://news.google.com/rss/search?"
            f"q={kw_encoded}+when:{hours}h&hl=en-US&gl=US&ceid=US:en"
        )

        feed = feedparser.parse(rss_url)

        for entry in feed.entries:
            if not hasattr(entry, "published_parsed") or entry.published_parsed is None:
                continue

            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if published < cutoff:
                continue

            source = "Google News"
            if hasattr(entry, "source") and hasattr(entry.source, "title"):
                source = entry.source.title

            articles.append({
                "title": entry.title.strip(),
                "link": entry.link.strip(),
                "published_dt": published,
                "published": published.strftime("%Y-%m-%d %H:%M UTC"),
                "source": source
            })

    return articles


def build_newsletter():
    newsletter = {}

    for company, cfg in COMPANIES.items():
        raw = fetch_google_news(cfg["keywords"], HOURS)

        filtered = []
        for a in raw:
            if passes_strict_filter(a["title"], cfg["strict"]):
                filtered.append(a)

        deduped = {}
        for a in filtered:
            key = (a["title"], a["link"])
            if key not in deduped or a["published_dt"] > deduped[key]["published_dt"]:
                deduped[key] = a

        sorted_articles = sorted(
            deduped.values(),
            key=lambda x: x["published_dt"],
            reverse=True
        )

        newsletter[company] = sorted_articles[:MAX_PER_COMPANY]

    return newsletter


# ===============================
# PDF
# ===============================

def generate_pdf(newsletter_data):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(PDF_NAME, pagesize=A4)
    content = []

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_items = sum(len(v) for v in newsletter_data.values())

    content.append(Paragraph("<b>LNG & Shipping – Daily Newsletter</b>", styles["Title"]))
    content.append(Spacer(1, 8))
    content.append(Paragraph(f"{today} · Last {HOURS}h · {total_items} articles", styles["Normal"]))
    content.append(Spacer(1, 16))

    for company, articles in newsletter_data.items():
        content.append(Paragraph(company, styles["Heading2"]))
        content.append(Spacer(1, 8))

        if not articles:
            content.append(Paragraph("No relevant news.", styles["Normal"]))
            content.append(Spacer(1, 10))
            continue

        for a in articles:
            text = (
                f"<b>{a['title']}</b><br/>"
                f"{a['source']} – {a['published']}<br/>"
                f"<a href='{a['link']}'>Open article</a>"
            )
            content.append(Paragraph(text, styles["Normal"]))
            content.append(Spacer(1, 10))

    doc.build(content)


# ===============================
# EMAIL
# ===============================

def send_email_with_pdf():
    outlook_user = os.environ["OUTLOOK_USER"]
    outlook_password = os.environ["OUTLOOK_PASSWORD"]
    to_email = os.environ["TO_EMAIL"]

    msg = EmailMessage()
    msg["Subject"] = f"LNG Daily Newsletter – {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    msg["From"] = outlook_user
    msg["To"] = to_email
    msg.set_content("Attached: LNG & Shipping daily newsletter (last 24 hours).")

    with open(PDF_NAME, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=PDF_NAME
        )

    with smtplib.SMTP("smtp.office365.com", 587) as smtp:
        smtp.starttls()
        smtp.login(outlook_user, outlook_password)
        smtp.send_message(msg)


# ===============================
# MAIN
# ===============================

if __name__ == "__main__":
    data = build_newsletter()
    generate_pdf(data)
    send_email_with_pdf()





