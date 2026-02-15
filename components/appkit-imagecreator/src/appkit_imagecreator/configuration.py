from pydantic import SecretStr

from appkit_commons.configuration.base import BaseConfig


class ImageGeneratorConfig(BaseConfig):
    google_api_key: SecretStr
    """required for Google image models (Imagen3, Imagen4)"""
    blackforestlabs_api_key: SecretStr
    """required for Black Forest Labs Flux models"""
    blackforestlabs_base_url: str | None = None
    openai_api_key: SecretStr
    """required for OpenAI images models (GPT-Image-1)"""
    openai_base_url: str | None = None
    uses_azure: bool = False
    """optional, for OpenAI-compatible endpoints, e.g. Azure OpenAI"""
    tmp_dir: str = "./uploaded_files"
    """temp directory for storing generated images, default Reflex.dev upload dir"""


prompt_list = [
    # 1. Aqua-haariges Anime-Mädchen
    "Erwachsenes Anime-Mädchen, langes aqua-glasiges Haar und Augen, einzelner linker Pferdeschwanz, hellgrünes traditionelles Kleid, hyperdetailliert, scharfer Fokus",  # noqa: E501
    # 3. Japanische Tengu-Fantasy-Render
    "Japanischer Tengu-Drache, dramatische stimmungsvolle Beleuchtung, filmische Atmosphäre, hohe Auflösung",  # noqa: E501
    # 4. Brüllender Löwenkönig
    "Mächtiger brüllender Löwe, mit einer Krone auf",
    # 9. Biolumineszierender Wal im Canyon
    "Enormer Wal, der durch den Antelope Canyon in glühendem biolumineszentem Wasser gleitet",  # noqa: E501
    # 10. Cartoon-Tiger mit Fächer
    "Cartoon-Tiger, der mit einem Blattfächer wedelt, Herbstblätter auf dem Boden, prägnante Linien, filmische Beleuchtung, ultra-detaillierte Umgebung",  # noqa: E501
    # 11. Klassisches Porträt im Öl-Stil
    "Porträt eines stoischen Gentleman, symmetrische Komposition, ruhiger Blick, malerische Details",  # noqa: E501
    # 12. Illustration eines Malerstudios
    "Innenillustration eines Künstlerateliers, weiche Herbstpalette, Gouache-Textur",
    # 13. Futuristische Stadtlandschaft 2100
    "Große Stadtlandschaft im Jahr 2100, atmosphärisch hyperrealistisch 16K, epische Komposition, filmische Beleuchtung",  # noqa: E501
    # 14. Fantasy-Insel-Portal
    "Fantasy-Insel mit volumetrischem magischem Portal, Figur in Wolken, Regenbogenlicht, Mittelschnitt, High-Detail-Stil",  # noqa: E501
    # 15. Feldbaum-Matte-Malerei
    "Einsamer volumiöser Baum im Sommer auf offenem Feld, Plein-Air-Stil, detailliert, realistisch",  # noqa: E501
    # 16. Futuristische Flugzeug-Kinematik
    "Kinematisches Konzept: futuristisches Flugzeug, das durch eine Neon-Stadtstraße fliegt, Tiefenschärfe-Unschärfe, dystopische Atmosphäre, High-Detail-Render, Lens-Flare",  # noqa: E501
    # 17. Welpen-Strandfoto
    "Nahaufnahme eines fotorealistischen Welpen mit Sonnenbrille am Sonnenuntergangsstrand, 4K HD, gestochen scharfe Details, skurrile Stimmung",  # noqa: E501
    # 18. Porträt eines erfahrenen Feuerwehrmanns
    "Porträt eines erfahrenen Feuerwehrmanns in schwerer Ausrüstung, scharfer Fokus, heroische Atmosphäre",  # noqa: E501
    # 19. Fantasy-Kanal-Ölgemälde
    "Kanal, flankiert von geschwungener Fantasy-Architektur, majestätische Komposition, Morgendämmerungsbeleuchtung, detailliert",  # noqa: E501
    # 20. Deutsches Reetdachhaus
    "Hochauflösendes Bild eines charmanten Backsteinhauses mit einem Reetdach am sandigen Ufer eines Nordseestrandes zur goldenen Stunde am Morgen. Detaillierte Ziegel- und Strohstrukturen, windgepeitschtes Dünengras im Vordergrund, weiches warmes Sonnenlicht, das natürliche Schatten wirft, subtiler Seenebel am Horizont, realistische Kameraperspektive",  # noqa: E501
]

styles_preset = {
    "Photographic": {
        "path": "/styles/photographic.webp",
        "prompt": "## Style hints: photorealistic 35 mm film-style photograph; natural color balance; ultra-high-definition 4K resolution; authentic film-grain texture; shallow depth-of-field with smooth bokeh; accurate lighting and surface detail",  # noqa: E501
    },
    "Cinematic": {
        "path": "/styles/cinematic.webp",
        "prompt": "## Style hints: dramatic widescreen cinemascope still; high-contrast lighting; rich cinematic color grading; subtle film-grain and vignette; epic composition; emotional atmosphere; high-budget production values",  # noqa: E501
    },
    "Digital Art": {
        "path": "/styles/digitalart.webp",
        "prompt": "## Style hints: ultra-detailed digital painting; painterly brush strokes; vibrant color palette; high-resolution matte-painting style; showcase-grade illustration for ArtStation",  # noqa: E501
    },
    "Concept Art": {
        "path": "/styles/conceptart.webp",
        "prompt": "## Style hints: widescreen concept art: character sheet and environment; dynamic composition; bold silhouettes; high-contrast lighting; subtle lens distortion; stylistic influences from Kim Jung Gi, Zabrocki & Jayison Devadas; trending on ArtStation",  # noqa: E501
    },
    "Sketch": {
        "path": "/styles/sketch.webp",
        "prompt": "## Style hints: hyper-detailed graphite pencil sketch; delicate linework; nuanced cross-hatching and shading; monochrome hand-drawn style; by Paul Cadden",  # noqa: E501
    },
    "Anime": {
        "path": "/styles/anime.webp",
        "prompt": "## Style hints: vibrant anime illustration; expressive large eyes; crisp cel-shading; dynamic poses and linework; detailed character design; featured on Pixiv & ArtStation",  # noqa: E501
    },
    "Cartoon": {
        "path": "/styles/cartoon.webp",
        "prompt": "## Style hints: stylized cartoon illustration; bold outlines; exaggerated, family-friendly character design; flat vibrant colors; dynamic composition; studio-quality render",  # noqa: E501
    },
    "Low Poly": {
        "path": "/styles/lowpoly.webp",
        "prompt": "## Style hints: low-poly isometric 3D render; clean geometric forms; flat shading; minimal polygon count; real-time engine quality; simple white background",  # noqa: E501
    },
}
