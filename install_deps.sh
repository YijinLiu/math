#!/bin/bash

set -e

sudo apt install libsixel1 texlive-latex-base texlive-latex-extra cm-super dvipng

pip3 install aiohttp libsixel matplotlib ptyprocess torch
