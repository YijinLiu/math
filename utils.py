from libsixel.encoder import Encoder, SIXEL_OPTFLAG_COLORS, SIXEL_OPTFLAG_OUTPUT
import matplotlib
import matplotlib.pyplot as plt
import re
import shutil
import string
import tempfile

def split_latex(latex_expr: str, columns: int) -> list[str]:
    if len(latex_expr) <= columns or not latex_expr.startswith("$") or not latex_expr.endswith("$"):
        return [latex_expr]

    simplified_latex_expr = latex_expr[1:len(latex_expr)-1]
    if simplified_latex_expr.startswith(r"\boxed{") and simplified_latex_expr.endswith("}"):
        simplified_latex_expr = simplified_latex_expr[7:len(simplified_latex_expr)-1]

    items = simplified_latex_expr.split(", ")
    lines = []
    line = ""
    def add_line(line: str):
        nonlocal lines
        lines.append("$" + line + "$")
    for item in items:
        if len(line) + 2 + len(item) <= columns:
            if line:
                line += ", "
            line += item
        elif not line:
            add_line(item)
        else:
            add_line(line)
            line = item
    if line:
        add_line(line)
    return lines

def split_llm_output_to_lines(text: str) -> list[str]:
    lines = []
    NUM_COLUMNS = shutil.get_terminal_size().columns
    line = ""
    in_latex = False

    def add_to_line(item: str) -> bool:
        nonlocal line, lines
        if len(line) + 1 + len(item) <= NUM_COLUMNS:
            if line:
                line += " "
            line += item
        elif not line:
            lines.extend(split_latex(item, NUM_COLUMNS))
            return True
        else:
            lines.append(line)
            line = item
        return False

    start = 0
    for i, ch in enumerate(text):
        if ch == "$":
            in_latex = not in_latex
        elif not in_latex and ch in string.whitespace:
            new_line = False
            if i > start:
                new_line = add_to_line(text[start:i])
            if ch == "\n":
                if line and not new_line:
                    lines.append(line)
                line = ""
            start = i + 1

    if start < len(text):
        add_to_line(text[start:])

    if line:
        lines.append(line)

    return lines

lb_re = re.compile(r"\\[([]\s+")
rb_re = re.compile(r"\s+\\[])]")

def beautify_llm_outout(text: str, use_sixel=False, use_html=False) -> str:
    text = text.replace("<s>", "")
    text = text.replace("</s>", "")
    text = text.replace("<｜begin▁of▁sentence｜>", "")
    text = text.replace("<｜end▁of▁sentence｜>", "")
    text = text.replace("$$", "$")
    text = lb_re.sub("$", text)
    text = rb_re.sub("$", text)
    if use_html:
        text = text.replace("\n", "\n<br>\n")
        text = text.replace("[INST]", "<b><i>")
        text = text.replace("[/INST]", "</b></i>")
    else:
        text = text.replace("[INST]", "\n----------\n")
        text = text.replace("[/INST]", "\n----------\n")
    text = "\n".join(split_llm_output_to_lines(text))
    if use_sixel:
        start = text.find("$")
        while start >= 0:
            end = text.find("$", start + 1)
            if end < 0:
                break
            end += 1
            latex_expr = text[start:end]
            print(latex_expr)
            png_file = latex_to_image(latex_expr)
            sixel_str = image_to_sixel(png_file)
            text = text[:start] + sixel_str + text[end:]
            start = text.find("$", end + len(sixel_str) - len(latex_expr))
    return text

def latex_to_image(latex_expr: str, font_size=16, dpi=200, img_size=(3, 0.3),
                   img_fmt="png") -> str:
    # Change font to Computer Modern.
    saved_font = matplotlib.rcParams["mathtext.fontset"]
    matplotlib.rcParams["mathtext.fontset"] = "cm"
    fig = plt.figure(figsize=img_size, dpi=dpi, layout="tight")
    fig.text(
        x=0.5,
        y=0.5,
        s=latex_expr,
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=font_size,
        usetex=True
    )
    # Restore the font.
    matplotlib.rcParams["mathtext.fontset"] = saved_font

    png_file=tempfile.NamedTemporaryFile(mode="w", suffix="." + img_fmt, prefix="latex_")
    png_file_name = png_file.name
    png_file.close()
    plt.savefig(png_file_name, format=img_fmt, bbox_inches="tight", pad_inches=0)
    return png_file_name

def image_to_sixel(img_file: str) -> str:
    encoder = Encoder()
    encoder.setopt(SIXEL_OPTFLAG_COLORS, "16")
    sixel_file = img_file + ".sixel"
    encoder.setopt(SIXEL_OPTFLAG_OUTPUT, sixel_file)
    encoder.encode(img_file)
    with open(sixel_file, "r") as file:
        return file.read()
