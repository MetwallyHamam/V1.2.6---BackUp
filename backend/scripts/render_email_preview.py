import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.notifications.email_template import branded_email_html


def main() -> None:
    output = Path(__file__).resolve().parents[2] / ".email-template-preview.html"
    output.write_text(
        branded_email_html(
            "You were mentioned on SR-2026-021186",
            "Metwally Hammam mentioned you in a support ticket.\n\n"
            "Please review the latest client update and confirm the next action.\n\n"
            "https://millensysonline.net/SupportHub/tickets/21186",
        ),
        encoding="utf-8",
    )
    print(output)


if __name__ == "__main__":
    main()
