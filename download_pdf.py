import os
from dotenv import load_dotenv
import imapclient
import pyzmail

load_dotenv()

EMAIL = os.getenv("EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
SENDER = os.getenv("SENDER")

required_vars = {
    "EMAIL": EMAIL,
    "APP_PASSWORD": APP_PASSWORD,
    "SENDER": SENDER,
}
missing_vars = [name for name, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(
        f"Missing required environment variables: {', '.join(missing_vars)}. "
        "Please check your .env file."
    )


def download_latest_pdf():
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    try:
        mail = imapclient.IMAPClient("imap.gmail.com", ssl=True)
    except Exception as e:
        print(f"Error connecting to IMAP server {"imap.gmail.com"}: {e}")
        return []

    try:
        mail.login(EMAIL, APP_PASSWORD)
    except Exception as e:
        print(f"Error logging in with provided credentials: {e}")
        return []

    try:
        mail.select_folder("INBOX", readonly=True)
        UIDs = mail.search(["X-GM-RAW", f"from:{SENDER} has:attachment"])
        if not UIDs:
            print("No emails found from", SENDER)
            mail.logout()
            return []

        UIDs.sort()
        latest_uid = UIDs[-1]
        raw_message = mail.fetch([latest_uid], ["BODY[]", "FLAGS"])
        message = pyzmail.PyzMessage.factory(raw_message[latest_uid][b"BODY[]"])

        pdf_paths = []
        for part in message.mailparts:
            if part.filename and part.filename.lower().endswith(".pdf"):
                pdf_path = os.path.join("downloads", part.filename)
                with open(pdf_path, "wb") as f:
                    f.write(part.get_payload())
                print(f"Downloaded PDF: {pdf_path}")
                pdf_paths.append(pdf_path)

        mail.logout()
        return pdf_paths
    except Exception as e:
        print(f"Error downloading PDFs: {e}")
        try:
            mail.logout()
        except:
            pass
        return []
