import tomllib
from pathlib import Path
from typing import Any

from rich import print
from typer import Exit


project_dir = Path.cwd()
src_dir = Path(__file__).parent / 'sample_project'

user_config = project_dir / '.config' / 'config.toml'
user_timesheet = project_dir / 'timesheet.txt'
user_img_dir = project_dir / 'images'
src_config = src_dir / '.config' / 'config.toml'


def load_config(path: Path) -> dict[str, Any]:
    with path.open('rb') as toml:
        return tomllib.load(toml)

try:
    data = load_config(user_config)
    is_inited = True
except FileNotFoundError:
    is_inited = False
    project_dir = src_dir
    data = load_config(src_config)


def init_project() -> None:
    from shutil import copyfile

    if is_inited:
        print(f'[red]Error: Project is already initiated in this directory! '
              f'See the config:\n[yellow]{str(user_config)}')
        raise Exit(1)
    else:
        Path.mkdir(user_config.parent, exist_ok=True)
        Path.mkdir(user_img_dir, exist_ok=True)

        copyfile(src_config, user_config)
        print('[green]Project created!')
        raise Exit


def inited_check() -> None:
    if not is_inited:
        print('[red]Error: This is not a project directory! '
              'Please run [cyan]hibari init[/cyan].\n'
              'If you already have it set up, run [cyan]cd '
              '"path/to/your/project/directory"[/cyan].')
        raise Exit(1)


ts_dict = data['timesheet']

what_to_print: str = ts_dict['what_to_print']
scale: int = ts_dict['scale']
pos: int = ts_dict['position']

crop_dict = data['crop']
crop: dict[str, int] = {
    'left': crop_dict['left'],
    'right': crop_dict['right'],
    'top': crop_dict['top'],
    'bottom': crop_dict['bottom']
}
border_clr: list[int] = crop_dict['border_color']  # YUV
stack_with_cropped: bool = crop_dict['stack_with_cropped']

colors: dict[str, list[int]] = data['colors']  # RGB

fps_dict = data['fps']
fps_num: int = fps_dict['fps_num']
fps_den: int = fps_dict['fps_den']

comp_dict = data['comparison_clip']
comp_str: str = comp_dict['comparison_source']
comp_src = Path(comp_str).resolve() if comp_str not in ['', './comp/cats.mp4'] else ''
first_frame: int = comp_dict['first_frame']
last_frame: int = comp_dict['last_frame']
comp_filler_start_length: int = comp_dict['comp_filler_start_length']
comp_filler_end_length: int = comp_dict['comp_filler_end_length']
start_clr: str = comp_dict['start_color']
end_clr: str = comp_dict['end_color']

mrg_dict = data['merge']
weight: list[float] = mrg_dict['weight']
lvl_thr: int = mrg_dict['level_threshold']
lvl_gamma: float = mrg_dict['level_gamma']
inscribe: bool = mrg_dict['inscribe']
invert: bool = mrg_dict['invert']

lsmas: bool = data['misc']['lsmas']
l_cachedir = project_dir / 'cache'
