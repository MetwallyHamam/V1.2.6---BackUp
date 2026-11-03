from app.modules.clients.models import Client
from app.modules.local_ai.routes import _client_candidates, _fallback_title, _match_client


def client(client_id: int, code: str, name: str) -> Client:
    return Client(id=client_id, status_id=1, code=code, name=name, is_active=True)


def test_client_detection_shortlist_and_catalog_mapping() -> None:
    alfa = client(1, "ALFA", "Alfa Scan Center")
    beta = client(2, "BETA", "Beta Hospital")

    candidates = _client_candidates(
        "Alfa Scan reports that PACS images are not reaching the workstation.",
        [beta, alfa],
        None,
    )

    assert candidates[0] is alfa
    assert _match_client("ALFA — Alfa Scan Center", candidates) is alfa
    assert _match_client("Beta Hospital", candidates) is beta
    assert _match_client("Invented Hospital", candidates) is None


def test_ticket_title_fallback_is_short_and_preserves_medical_terms() -> None:
    title = _fallback_title(
        "DICOM modality worklist is unavailable on CT. Additional diagnostic details follow."
    )

    assert title == "DICOM modality worklist is unavailable on CT"
    assert len(_fallback_title("x" * 500)) == 160


def test_arabic_client_name_is_shortlisted_and_mapped() -> None:
    techno = client(1, "TECHNO-MATROUH", "تكنو مطروح")
    other = client(2, "CAIRO", "مستشفى القاهرة")

    candidates = _client_candidates(
        "تكنو مطروح صور العادية ما بتوصلش من اللوكال للرئيسى",
        [other, techno],
        None,
    )

    assert candidates[0] is techno
    assert _match_client("TECHNO-MATROUH — تكنو مطروح", candidates) is techno
    assert _match_client("تكنو مطروح", candidates) is techno
