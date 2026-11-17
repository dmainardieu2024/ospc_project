"""Organise one completed job's output files by purpose."""
import argparse
from pathlib import Path

def organize(root):
    root = Path(root)
    files = [p for p in root.iterdir() if p.is_file()]
    if (root / 'data').is_dir():
        files += [p for p in (root / 'data').iterdir() if p.is_file()]
    for p in files:
        if p.name == 'README.md':
            continue
        if p.suffix in {'.png', '.pdf'}:
            section = 'figures'
        elif p.name.endswith('_summary.json') and p.name != 'profile_summary.json' or p.suffix in {'.csv', '.npy'}:
            section = 'measurements'
        else:
            section = 'run_details'
        target = root / section / p.name
        if target.exists():
            raise FileExistsError(target)
        target.parent.mkdir(exist_ok=True)
        p.rename(target)
    data = root / 'data'
    if data.is_dir() and not any(data.iterdir()):
        data.rmdir()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    organize(parser.parse_args().directory)
