#!/usr/bin/env python3

import os
import subprocess
import sys


def main():
    print("Hello World!")
    print("Python version")
    print(sys.version)
    print("Python executable")
    print(sys.executable)
    print("Current working directory")
    print(os.getcwd())
    x = True
    return x
