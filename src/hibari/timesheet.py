import re
from os import listdir
from os.path import join, isfile, splitext

from natsort import os_sorted

from rich import print
from typer import Exit, Abort

from .config import (
    colors,
    is_inited,
    user_img_dir,
    user_timesheet,
)


if is_inited:
    imgseq = [img for img in os_sorted(listdir(user_img_dir))
              if isfile(join(user_img_dir, img)) and not splitext(img)[0].endswith('#')]
    basenames = [splitext(bn)[0] for bn in imgseq]

    file_dict = dict(zip(basenames, imgseq))


def images_in_directory_check() -> None:
    if len(imgseq) == 0:
        print(f'[red]Error: No images found in the subdirectory! Place images in:\n'
              f'[yellow]{str(user_img_dir)}')
        raise Exit(1)


def create_timesheet(default_timing: int) -> None:
    def write_ts(mode: str) -> None:
        full_lines = [bn + '  ' + str(default_timing) + '\n' for bn in basenames]
        with open(user_timesheet, mode, encoding='utf-8') as ts:
            ts.writelines(full_lines)

    try:
        write_ts(mode='x')
        print('[green]Timesheet created!')
    except FileExistsError:
        print(f'[red]Warning: Timesheet is already exists:\n'
              f'[yellow]{str(user_timesheet)}[/yellow]\n'
              f'Rewriting will erase all comments, color fillers, and other formatting. Rewrite?')

        i = input('[y/N]:')
        if i in ['y', 'Y']:
            write_ts(mode='w')
            print('[green]Timesheet rewritten!')
        else:
            raise Abort



def get_timings_from_timesheet(ts_name: str) -> list[tuple[str, str, str, str]]:
    ts_loc = user_timesheet.parent / f'{ts_name}.txt'

    try:
        with ts_loc.open(encoding='utf-8') as timesheet:
            ts_lines = [l.splitlines() for l in timesheet.readlines()]
    except FileNotFoundError:
        print('[red]Error: Timesheet file not found! Run '
              '[cyan]hibari timesheet[/cyan] to create a timesheet file.')
        if ts_name != 'timesheet':
            print(f'[red]Notice that you are currently trying to read the timesheet '
                  f'from a non-standard file named [yellow]{ts_name}.txt[/yellow].')
        raise Exit(1)

    ts_formatted_lines = [l for nested_lines in ts_lines for l in nested_lines
                          if l != ''
                          if not l.startswith('#')]
    try:
        start_index = ts_formatted_lines.index('start') + 1
        ts_formatted_lines = ts_formatted_lines[start_index:]
    except ValueError:
        pass
    try:
        end_index = ts_formatted_lines.index('end')
        ts_formatted_lines = ts_formatted_lines[:end_index]
    except ValueError:
        pass


    names = list[str]()
    timings = list[int]()
    comments = list[str]()

    color_lines = 0
    for i, ln in enumerate(ts_formatted_lines):
        try:
            clr_re = re.search(r'^(\w+)\D+(\d+)\s*(.*)', ln)
            clr_name, clr_timing, clr_com = clr_re.groups()

            if clr_name not in colors:
                raise AttributeError

            names.append(clr_name)
            timings.append(int(clr_timing))
            comments.append(clr_com)

            color_lines += 1
        except AttributeError:
            try:
                basename = basenames[i - color_lines]

                img_re = re.search(fr'^({basename})\D+(\d+)\s*(.*)', ln)
                img_name, img_timing, img_com = img_re.groups()

                names.append(img_name)
                timings.append(int(img_timing))
                comments.append(img_com)
            except (AttributeError, IndexError):
                print(
                    f'[red]Error: Timings are not found! Problem line:\n'
                    f'\t[yellow]{ln}[/yellow]\n'
                    f'If you added timesheet lines or images after the timesheet '
                    f'was created, please check if you forgot to match them.\n'
                    f'Also, check if you followed the template:\n'
                    f'\t[yellow]Comment before content.\n\n'
                    f'\tstart\n\n\n'
                    f'\twhite  8\n\n'
                    f'\t# per-line comment\n'
                    f'\t{basenames[0]}  4  in-line comment\n\n\n'
                    f'\tend\n\n'
                    f'\tComment after content. All comments and color lines are '
                    f'optional, of course, including \'start\' and \'end\'.'
                )
                raise Exit(1)


    def time_list(in_list: list[str] | list[int]) -> list[str]:
        return [str(i) for i, t in zip(in_list, timings) for _ in range(t)]

    names_t = time_list(names)
    timings_t = time_list(timings)
    comments_t = time_list(comments)
    lines_t = time_list(ts_formatted_lines)

    timed_zip = zip(names_t, timings_t, comments_t, lines_t)

    return list(timed_zip)
