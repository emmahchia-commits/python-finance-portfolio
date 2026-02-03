!pip install feedparser reportlab
import os
import smtplib
from email.message import EmailMessage
import feedparser
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

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
        # keep keywords if you want, but STRICT is what will decide what stays
        "keywords": ["Capital Clean Energy Carriers", "Capital Clean Energy Carriers Corp.", "CCEC"],
        # THIS is the key: remove broad stuff like "Capital Clean Energy"
        "strict": ["Capital Clean Energy Carriers", "CCEC"]
    },
    "Nakilat": {
        "keywords": ["Nakilat", "Qatar Gas Transport", "QGTS"],
        "strict": ["Nakilat", "QGTS"]
    },
    "Hyundai Heavy Industries (HHI)": {
        "keywords": ["Hyundai Heavy Industries", "HHI"],
        "strict": ["Hyundai Heavy Industries"]  # avoid noisy acronym
    },
    "Hanwha Ocean": {
        "keywords": ["Hanwha Ocean", "DSME", "Daewoo Shipbuilding"],
        "strict": ["Hanwha Ocean", "Daewoo Shipbuilding", "DSME"]
    },
    "Samsung Heavy Industries (SHI)": {
        "keywords": ["Samsung Heavy Industries", "SHI"],
        "strict": ["Samsung Heavy Industries"]  # avoid noisy acronym
    },
    "MOL": {
        "keywords": ["Mitsui O.S.K.", "Mitsui O.S.K. Lines", "MOL"],
        "strict": ["Mitsui O.S.K.", "Mitsui O.S.K. Lines"]  # avoid noisy acronym
    },
    "NYK": {
        "keywords": ["NYK", "Nippon Yusen", "Nippon Yusen Kaisha"],
        "strict": ["Nippon Yusen", "Nippon Yusen Kaisha"]  # avoid noisy acronym
    },
    "Maran Gas": {
        "keywords": ["Maran Gas", "Maran Gas Maritime"],
        "strict": ["Maran Gas"]
    },
    "Seapeak Maritime": {
        "keywords": ["Seapeak", "Seapeak Maritime"],
        "strict": ["Seapeak"]
    },
    "GasLog": {
        "keywords": ["GasLog", "GasLog Partners LP", "GLOP-PA"],
        "strict": ["GasLog", "GLOP"]  # keep it broad-ish but still specific
    },
    "Hyundai Samho Heavy Industries": {
        "keywords": ["Hyundai Samho", "Hyundai Samho Heavy Industries"],
        "strict": ["Hyundai Samho"]
    },
    "Hudong-Zhonghua": {
        "keywords": ["Hudong-Zhonghua", "Hudong Zhonghua", "Hudong-Zhonghua Shipbuilding"],
        "strict": ["Hudong-Zhonghua", "Hudong Zhonghua"]
    }
}


def passes_strict_filter(article_title, strict_keywords):
    if not strict_keywords:
        return True
    t = article_title.lower()
    return any(sk.lower() in t for sk in strict_keywords)



    def fetch_google_news(keywords, hours=24, hl="en-US", gl="US", ceid="US:en"):
    """
    Pulls Google News RSS items for each keyword and keeps only items with published date >= now-<hours>.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles = []

    for kw in keywords:
        kw_encoded = quote_plus(kw)
        rss_url = (
            "https://news.google.com/rss/search?"
            f"q={kw_encoded}+when:{hours}h&hl={hl}&gl={gl}&ceid={ceid}"
        )

        feed = feedparser.parse(rss_url)

        for entry in getattr(feed, "entries", []):
            if not hasattr(entry, "published_parsed") or entry.published_parsed is None:
                continue

            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if published < cutoff:
                continue

            source = "Google News"
            if hasattr(entry, "source") and entry.source and hasattr(entry.source, "title"):
                source = entry.source.title

            articles.append({
                "title": entry.title.strip(),
                "link": entry.link.strip(),
                "published_dt": published,
                "published": published.strftime("%Y-%m-%d %H:%M UTC"),
                "source": source
            })

    return articles




def build_newsletter(companies_dict, hours=24, max_per_company=8):
    newsletter_data = {}

    for company, config in companies_dict.items():
        keywords = config["keywords"]
        strict = config.get("strict")

        raw = fetch_google_news(keywords, hours=hours)

        # Apply strict title filter (this is what kills the random macro articles)
        filtered = [a for a in raw if passes_strict_filter(a["title"], strict)]

        # dedupe across keywords by (title, link)
        unique = {}
        for a in filtered:
            key = (a["title"], a["link"])
            if key not in unique or a["published_dt"] > unique[key]["published_dt"]:
                unique[key] = a

        articles = sorted(unique.values(), key=lambda x: x["published_dt"], reverse=True)
        newsletter_data[company] = articles[:max_per_company]

    return newsletter_data




def send_email_with_pdf(pdf_path: str, subject: str, body: str):
    outlook_user = os.environ["OUTLOOK_USER"]
    outlook_password = os.environ["OUTLOOK_PASSWORD"]
    to_email = os.environ["TO_EMAIL"]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = outlook_user
    msg["To"] = to_email
    msg.set_content(body)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=os.path.basename(pdf_path),
    )

    with smtplib.SMTP("smtp.office365.com", 587) as smtp:
        smtp.starttls()
        smtp.login(outlook_user, outlook_password)
        smtp.send_message(msg)




        


def generate_pdf(newsletter_data, filename="LNG_Daily_Newsletter.pdf", hours=24):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(filename, pagesize=A4)

    content = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    content.append(Paragraph(f"<b>LNG & Shipping – Daily Newsletter (Last {hours}h)</b>", styles["Title"]))
    content.append(Spacer(1, 8))
    content.append(Paragraph(today, styles["Normal"]))
    content.append(Spacer(1, 16))

    # quick index / overview
    total_articles = sum(len(v) for v in newsletter_data.values())
    content.append(Paragraph(f"Companies covered: {len(newsletter_data)} | Total items: {total_articles}", styles["Normal"]))
    content.append(Spacer(1, 16))

    for idx, (company, articles) in enumerate(newsletter_data.items(), start=1):
        content.append(Paragraph(company, styles["Heading2"]))
        content.append(Spacer(1, 8))

        if not articles:
            content.append(Paragraph("No relevant news in the last period.", styles["Normal"]))
            content.append(Spacer(1, 10))
        else:
            for a in articles:
                # Keep it simple and readable
                text = (
                    f"<b>{a['title']}</b><br/>"
                    f"{a['source']} – {a['published']}<br/>"
                    f"<a href='{a['link']}'>Open article</a>"
                )
                content.append(Paragraph(text, styles["Normal"]))
                content.append(Spacer(1, 10))

        

    doc.build(content)




HOURS = 24
MAX_PER_COMPANY = 8  # tweak: 5-10 is usually good

newsletter_data = build_newsletter(COMPANIES, hours=HOURS, max_per_company=MAX_PER_COMPANY)

# sanity check counts
{c: len(v) for c, v in newsletter_data.items()}



generate_pdf(newsletter_data, filename="LNG_Daily_Newsletter.pdf", hours=HOURS)

pdf_name = "LNG_Daily_Newsletter.pdf"
generate_pdf(newsletter_data, filename=pdf_name, hours=HOURS)

send_email_with_pdf(
    pdf_path=pdf_name,
    subject=f"LNG Newsletter (last {HOURS}h)",
    body="Attached: today's LNG & Shipping news (last 24 hours)."
)




