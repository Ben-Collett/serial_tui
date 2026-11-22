from textual.theme import Theme


def create_theme(name: str, properties: dict) -> Theme | None:
    try:
        metadata = properties.get("metadata", {})
        colors = properties.get("color") or properties.get("colors") or {}
        variables = properties.get("variables", {})

        primary = colors.get("primary")
        if not primary:
            return None

        return Theme(
            name=name,
            primary=primary,
            secondary=colors.get("secondary"),
            warning=colors.get("warning"),
            error=colors.get("error"),
            success=colors.get("success"),
            accent=colors.get("accent"),
            foreground=colors.get("foreground"),
            background=colors.get("background"),
            surface=colors.get("surface"),
            panel=colors.get("panel"),
            boost=colors.get("boost"),
            dark=metadata.get("dark", True),
            luminosity_spread=metadata.get("luminosity_spread", 0.15),
            text_alpha=metadata.get("text_alpha", 0.95),
            variables=variables if variables else {},
        )
    except Exception:
        return None
