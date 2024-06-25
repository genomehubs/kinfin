#!/usr/bin/env python3

import os
import sys


def main():
    print("Python version")
    print(sys.version)
    print("Python executable")
    print(sys.executable)
    print("Current working directory")
    print(os.getcwd())
    return True
