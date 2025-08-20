import os
import shutil
from typing import List, Optional


def check_file(filepath: Optional[str], install_kinfin: bool = False) -> None:
    """
    Check if a file exists.

    Args:
        filepath (str): Path to the file to be checked.

    Raises:
        FileNotFoundError: If the file does not exist.
    """

    if filepath is not None and not os.path.isfile(filepath):
        error_msg = f"[ERROR] - file {filepath} not found."
        if install_kinfin:
            error_msg += " Please run the install script to download kinfin."
        raise FileNotFoundError(error_msg)


def setup_dirs(output_dir, attributes: List[str]) -> None:
    files_to_keep = {
        f for f in os.listdir(output_dir) if f.endswith(".status") or f == "config.txt"
    }

    if os.path.exists(output_dir):
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if item not in files_to_keep:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
    os.makedirs(output_dir, exist_ok=True)
    for attribute in attributes:
        os.makedirs(os.path.join(output_dir, attribute), exist_ok=True)
