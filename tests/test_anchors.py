from src.domain.anchors import extract_job_anchors
from src.domain.models import JobPosting


def test_extract_job_anchors_sections_and_skills() -> None:
    job = JobPosting(
        external_id="1",
        source="rss",
        url="https://example.com/j1",
        title="Desenvolvedor Flutter",
        company="Acme",
        location="Remoto",
        description=(
            "Requisitos\n- Flutter\n- SQL\nResponsabilidades\n- Construir features\n"
            "Diferenciais\n- Power BI\nAbout\n- Produto com impacto"
        ),
    )

    anchors = extract_job_anchors(job)
    assert "flutter" in anchors.top_skills
    assert any("construir" in item for item in anchors.responsibilities)
    assert any("power bi" in item for item in anchors.nice_to_have)
