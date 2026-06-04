
def not_reigistered_theme(theme, default_theme):
    return f"Theme '{theme}' is not a registered theme. Using '{default_theme}'."


def unknown_command(text):
    return "unknown command '{text}' — use !! to send literal '!', or use a valid command."
