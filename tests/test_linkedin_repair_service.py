from src.services.linkedin_repair_service import _clean_repaired_job


def test_clean_repaired_job_collapses_duplicate_title_and_company() -> None:
    candidate = {
        "id": "job-1",
        "run_id": "run-1",
        "external_id": "https://www.linkedin.com/jobs/view/1",
        "url": "https://www.linkedin.com/jobs/view/1",
        "title": "Mes Developermes Developer",
        "company": "Vdart DigitalVdart Digital",
        "location": "Brasil (Remoto)",
        "description": "MES DeveloperMES Developer Vdart Digital Brasil (Remoto) Avaliando candidaturas Promovida Candidatura simplificada",
        "score": 10,
        "score_reasons": "",
        "anchors_json": "{}",
        "score_breakdown_json": "{}",
        "recommendation": "SKIP",
        "status": "new",
    }
    enriched = {
        "url": "https://www.linkedin.com/jobs/view/1",
        "title": "Mes Developermes Developer",
        "company": "Vdart DigitalVdart Digital",
        "location": "Brasil (Remoto)",
        "description": "MES DeveloperMES Developer Vdart Digital Brasil (Remoto) Avaliando candidaturas Promovida Candidatura simplificada",
    }

    cleaned = _clean_repaired_job(candidate, enriched)

    assert cleaned["title"] == "Mes Developer"
    assert cleaned["company"] == "Vdart Digital"
    assert "Candidatura simplificada" not in cleaned["description"]


def test_clean_repaired_job_keeps_long_detail_description() -> None:
    candidate = {
        "id": "job-2",
        "run_id": "run-2",
        "external_id": "https://www.linkedin.com/jobs/view/2",
        "url": "https://www.linkedin.com/jobs/view/2",
        "title": "Application Security Engineer",
        "company": "Nichols Digital Ltd",
        "location": "Remote",
        "description": "short fallback",
        "score": 10,
        "score_reasons": "",
        "anchors_json": "{}",
        "score_breakdown_json": "{}",
        "recommendation": "SKIP",
        "status": "new",
    }
    enriched = {
        "url": "https://www.linkedin.com/jobs/view/2",
        "title": "Application Security Engineer",
        "company": "Nichols Digital Ltd",
        "location": "Remote",
        "description": "A large gaming firm is looking for an Application Security Engineer with strong Java, Python and cloud security experience.",
    }

    cleaned = _clean_repaired_job(candidate, enriched)

    assert cleaned["title"] == "Application Security Engineer"
    assert cleaned["company"] == "Nichols Digital Ltd"
    assert cleaned["description"].startswith("A large gaming firm")
