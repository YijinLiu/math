import click
import click_repl
from google import genai
from openai import OpenAI
import os
from prompt_toolkit.history import FileHistory
import timeit

from utils import *

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)

@cli.command()
def repl():
    prompt_kwargs = {
        "history": FileHistory(os.path.expanduser("~/.api_math_llm/history")),
        "message": "api-math> "
    }
    click.echo("Run ':help' for help information, or ':quit' to quit.")
    click_repl.repl(click.get_current_context(), prompt_kwargs=prompt_kwargs)

@cli.command()
@click.argument("query")
@click.option("--api_key", type=str)
@click.option("--model", type=str, default="o1-mini")
@click.option("--use_sixel", type=bool, default=False)
@click.option("--use_html", type=bool, default=False)
def openai(query: str, api_key: str, model: str, use_sixel: bool, use_html: bool):
    start = timeit.default_timer()
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=[
            #{
            #    "role": "developer",
            #    "content": "You are a helpful assistant that solve math problems.",
            #},
            {
                "role": "user",
                "content": query,
            },
        ])
    output = completion.choices[0].message.content
    click.echo(beautify_llm_outout(output, use_sixel=use_sixel, use_html=use_html))
    end = timeit.default_timer()
    click.echo(f"{end-start} seconds used.")

@cli.command()
@click.argument("query")
@click.option("--api_key", type=str)
@click.option("--model", type=str, default="deepseek-reasoner")
@click.option("--use_sixel", type=bool, default=False)
@click.option("--use_html", type=bool, default=False)
def deepseek(query: str, api_key: str, model: str, use_sixel: bool, use_html: bool):
    start = timeit.default_timer()
    client = OpenAI(api_key=api_key,  base_url="https://api.deepseek.com")
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that solve math problems.",
            },
            {
                "role": "user",
                "content": query,
            },
        ])
    output = completion.choices[0].message.content
    click.echo(beautify_llm_outout(output, use_sixel=use_sixel, use_html=use_html))
    end = timeit.default_timer()
    click.echo(f"{end-start} seconds used.")

@cli.command()
@click.argument("query")
@click.option("--api_key", type=str)
@click.option("--model", type=str, default="gemini-2.0-flash-exp")
@click.option("--use_sixel", type=bool, default=False)
@click.option("--use_html", type=bool, default=False)
def gemini(query: str, api_key: str, model: str, use_sixel: bool, use_html: bool):
    start = timeit.default_timer()
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model, contents=query)
    click.echo(beautify_llm_outout(response.text, use_sixel=use_sixel, use_html=use_html))
    end = timeit.default_timer()
    click.echo(f"{end-start} seconds used.")

if __name__ == "__main__":
    cli()
