from src.domain.models import JobPosting


def build_dm(job: JobPosting, candidate_name: str) -> str:
    return (
        f"Olá! Sou {candidate_name} e vi a vaga {job.title} na {job.company}. "
        "Tenho interesse e aderência técnica; posso enviar CV adaptado."
    )


def build_email(job: JobPosting, candidate_name: str) -> str:
    return (
        f"Assunto: Interesse na vaga {job.title}\n\n"
        f"Olá,\nMeu nome é {candidate_name} e gostaria de me candidatar à vaga {job.title}. "
        "Tenho projetos e experiências compatíveis com a descrição "
        "e fico disponível para conversar."
    )
