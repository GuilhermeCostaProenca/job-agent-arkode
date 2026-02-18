from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_outreach_drafts(
    feed_item: dict[str, Any],
    profile: dict[str, Any],
    style_vector: dict[str, Any],
    artifacts_dir: Path,
) -> dict[str, str]:
    feed_id = str(feed_item.get("id", "manual"))
    text = str(feed_item.get("text", ""))
    name = str(profile.get("name", "Candidate"))
    directness = float(style_vector.get("directness", 0.0))

    comment = artifacts_dir / f"outreach_comment_{feed_id}.txt"
    dm = artifacts_dir / f"outreach_dm_{feed_id}.txt"
    email = artifacts_dir / f"outreach_email_{feed_id}.txt"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    comment.write_text(
        (
            "Comentário sugerido:\n"
            f"Oi! Vi seu post sobre oportunidade ({text[:80]}...). "
            f"Sou {name} e tenho interesse em contribuir."
        ),
        encoding="utf-8",
    )
    dm.write_text(
        (
            f"Olá! Sou {name}. Vi o sinal de contratação e tenho interesse na oportunidade. "
            f"Posso compartilhar CV adaptado. Tom direto={directness:.1f}."
        ),
        encoding="utf-8",
    )
    email.write_text(
        (
            "Assunto: Interesse em oportunidade\n\n"
            f"Olá, sou {name}. Vi a publicação sobre contratação e gostaria de me apresentar. "
            "Posso enviar materiais alinhados e aguardo retorno."
        ),
        encoding="utf-8",
    )

    return {
        "comment": str(comment),
        "dm": str(dm),
        "email": str(email),
    }
