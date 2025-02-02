def beautify_llm_outout(text: str) -> str:
    text = text.replace("<s>", "")
    text = text.replace("\n", "\n<br>\n")
    text = text.replace("[INST]", "<b><i>")
    text = text.replace("[/INST]", "</b></i>")
    return text
