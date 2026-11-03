from app.core.config import Settings
from app.modules.notifications.email_template import branded_email_html, frontend_url


def test_frontend_base_url_includes_supporthub_path() -> None:
    settings = Settings(
        app_env="test",
        secret_key="test-secret-key-with-more-than-thirty-two-characters",
        frontend_origin="https://millensysonline.net",
        application_path_base="/SupportHub/backend",
    )
    assert settings.frontend_base_url == "https://millensysonline.net/SupportHub"


def test_frontend_base_url_supports_root_deployment() -> None:
    settings = Settings(
        app_env="test",
        secret_key="test-secret-key-with-more-than-thirty-two-characters",
        frontend_origin="https://support.example.com",
        application_path_base="",
    )
    assert settings.frontend_base_url == "https://support.example.com"


def test_explicit_frontend_base_url_and_ticket_links_include_supporthub() -> None:
    settings = Settings(
        app_env="test",
        secret_key="test-secret-key-with-more-than-thirty-two-characters",
        FRONTEND_BASE_URL="https://millensysonline.net/SupportHub/",
    )
    assert frontend_url(settings.frontend_base_url, "/tickets/44") == "https://millensysonline.net/SupportHub/tickets/44"
    assert frontend_url(settings.frontend_base_url, "/SupportHub/tickets/44") == "https://millensysonline.net/SupportHub/tickets/44"


def test_branded_html_template_has_action_and_required_footer() -> None:
    url = "https://millensysonline.net/SupportHub/tickets/44"
    rendered = branded_email_html("Ticket assigned", f"A ticket needs attention.\n\n{url}")
    assert f'href="{url}"' in rendered
    assert "MILLENSYS" in rendered
    assert "Technology for a Healthier Globe" in rendered
    assert "Automated notification from the Support Hub Platform" in rendered
    assert "© 2026 Millensys." in rendered
