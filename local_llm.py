import os
import timeit

import click
import click_repl
from prompt_toolkit.history import FileHistory

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

from utils import *

class LLM(object):
    def __init__(self, model_name: str):
        print(f"Loading {model_name} ...")
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            torch_dtype=torch.bfloat16,
        )
        LLM._model_name = model_name

    _instance = None
    @classmethod
    def instance(cls, model_name: str):
        if cls._instance:
            if cls._instance._model_name == model_name:
                return cls._instance
            del cls._instance
        cls._instance = LLM(model_name)
        return cls._instance


@click.group(invoke_without_command=True)
@click.option("--model_name", default="mistralai/Mathstral-7b-v0.1",
              help="deepseek-ai/DeepSeek-R1-Distill-Llama-8B etc.")
@click.pass_context
def cli(ctx, model_name: str):
    ctx.obj = LLM.instance(model_name)
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)

@cli.command()
@click.pass_obj
def repl(obj):
    pos = obj._model_name.find("/")
    short_name = obj._model_name[pos+1:]
    prompt_kwargs = {
        "history": FileHistory(os.path.expanduser("~/.local_math_llm/history")),
        "message": short_name + "> "
    }
    click.echo("Run ':help' for help information, or ':quit' to quit.")
    click_repl.repl(click.get_current_context(), prompt_kwargs=prompt_kwargs)

@cli.command()
@click.argument("query")
@click.option("--max_new_tokens", type=int, default=1024, help="Max number of new tokens.")
@click.option("--use_sixel", type=bool, default=False)
@click.option("--use_html", type=bool, default=False)
@click.pass_obj
def search(obj, query: str, max_new_tokens: int, use_sixel: bool, use_html: bool):
    start = timeit.default_timer()
    llm = obj
    prompt = [{"role": "user", "content": query}]
    tokenized_prompt = llm._tokenizer.apply_chat_template(
        prompt,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt").to(llm._model.device)
    outputs = llm._model.generate(**tokenized_prompt, max_new_tokens=max_new_tokens)
    decoded_output = llm._tokenizer.decode(outputs[0])
    click.echo(beautify_llm_outout(decoded_output, use_sixel=use_sixel, use_html=use_html))
    end = timeit.default_timer()
    click.echo(f"{end-start} seconds used.")

if __name__ == "__main__":
    cli()
