def __pad_line(line: str, width: int = 80) -> str:
    """
    Pad a line to a specific width with spaces.
    Args:
        line (str): The line to pad.
        width (int): The width to pad to.
    Returns:
        str: The padded line.
    """
    return line.center(width, "=")


def print_instruction(content: list[str], need_confirmation: bool = True):
    """
    Print instructions for the user.
    Args:
        content (str): The content to print.
    """
    for line in content:
        print(__pad_line(line))
    if not need_confirmation:
        return
    content = input(__pad_line("Press Enter to continue...")+'\n').strip()
    print(__pad_line("Continuing..."))
    return content