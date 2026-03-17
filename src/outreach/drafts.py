from __future__ import annotations

from pathlib import Path


def generate_outreach_drafts(
    feed_item: dict[str, object],
    profile: dict[str, object],
    style_vector: dict[str, object],
    artifacts_dir: Path,
) -> dict[str, str]:
    text = str(feed_item.get("text", ""))
    name = str(profile.get("name", "Candidate"))
    directness = float(style_vector.get("directness", 0.0))

    comment_content = (
        "Comentario sugerido:\n"
        f"Oi! Vi seu post sobre oportunidade ({text[:80]}...). "
        f"Sou {name} e tenho interesse em contribuir."
    )
    dm_content = (
        f"Ola! Sou {name}. Vi o sinal de contratacao e tenho interesse na oportunidade. "
        f"Posso compartilhar CV adaptado. Tom direto={directness:.1f}."
    )
    email_content = (
        "Assunto: Interesse em oportunidade\n\n"
        f"Ola, sou {name}. Vi a publicacao sobre contratacao e gostaria de me apresentar. "
        "Posso enviar materiais alinhados e aguardo retorno."
    )

    comment_path = artifacts_dir / f"outreach_comment_{feed_item.get('id', 'feed')}.txt"
    dm_path = artifacts_dir / f"outreach_dm_{feed_item.get('id', 'feed')}.txt"
    email_path = artifacts_dir / f"outreach_email_{feed_item.get('id', 'feed')}.txt"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    comment_path.write_text(comment_content, encoding="utf-8")
    dm_path.write_text(dm_content, encoding="utf-8")
    email_path.write_text(email_content, encoding="utf-8")

    return {"comment": comment_content, "dm": dm_content, "email": email_content}
