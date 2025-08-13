def print_instruction(content: list[str]):
    """
    Print instructions for the user.
    Args:
        content (str): The content to print.
    """
    _width = 80
    content.append("Press *enter* to continue...")
    for line in content:
        line = line.center(_width, "=")
        print(line)
    input()
    print("Continuing...".center(_width, "="))
