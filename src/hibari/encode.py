import re
import subprocess
from typing import BinaryIO, cast
from pathlib import Path

from vapoursynth import VideoNode

from rich import box, print
from rich.table import Table
from typer import Abort, Exit

from .config import project_dir
from .script import nodes_desc, vsscript


def encode_out_nodes(
    ts_name: str,
    binary: str,
    args: str,
    in_node_index: str,
    available_nodes: bool,
    verbose: bool,
    fullargs: str | None,
    resize_val: int | None,
) -> None:
    nodes = vsscript(ts_name, quiet=True, resize_val=resize_val)
    res = '' if resize_val is None else ' ' + str(resize_val) + 'p'

    if fullargs:
        binary = fullargs.split()[0]

    is_x = binary.startswith('x264')
    is_ff = binary.startswith('FFmpeg') or binary.startswith('ffmpeg')


    def list_available_nodes() -> tuple[list[int], Table]:    
        table = Table(title='available nodes', box=box.SIMPLE, show_header=False)

        table.add_column(style='cyan', justify='center')
        table.add_column(style='yellow', no_wrap=True)
        table.add_column(style='yellow', no_wrap=True)

        available_indices = list[int]()
        for i, name, _ in nodes:
            if name in nodes_desc.keys():
                table.add_row(str(i), name, nodes_desc[name])
                available_indices.append(i)

        return available_indices, table


    def parse_input_nodes(in_nodes: str) -> list[int]:
        '''Parse user text input to a list of indices.'''
        _in_nodes = re.split(r'\D', in_nodes)
        try:
            if '' in _in_nodes:
                parsed = list(range(int(_in_nodes[0]), int(_in_nodes[2]) + 1))
            else:
                parsed = sorted([int(n) for n in _in_nodes])
        except:
            raise SyntaxError
        else:
            return parsed


    def check_indices(available_indices: list[int], table: Table) -> list[int]:
        try:
            indices = parse_input_nodes(in_node_index)
            for i in indices:
                if i not in available_indices:
                    raise ValueError
        except SyntaxError:
            print('[red]Error: Output nodes were entered incorrectly!\n'
                  'Use [cyan]3[/cyan] for a single node, [cyan]0,3,4[/cyan] for separate '
                  'nodes, and [cyan]0..3[/cyan] for ranges.')
            raise Exit(1)
        except ValueError:
            print('[red]Error: Invalid node index entered.')
            print(table)
            raise Exit(1)
        else:
            return indices


    def get_shell_line() -> str:
        from shutil import which

        x_bin = f'{binary} --demuxer y4m'
        x_def_args = '--preset veryslow --crf 13.5'
        x_info = '--colormatrix bt709 --transfer bt709 --colorprim bt709 -o "./clips/{i}{name}{res}.mp4" -'
        ff_bin = f'{binary} -y -i - -c:v libx264'
        ff_def_args = '-preset veryslow -crf 13.5'
        ff_info = '-x264-params "colormatrix=bt709:transfer=bt709:colorprim=bt709" "./clips/{i}{name}{res}.mp4"'

        is_def = args == ff_def_args
        line = '{binary} {args} {info}'.format(
            binary=x_bin if is_x else ff_bin,
            args=x_def_args if is_x and is_def else ff_def_args if is_ff else args,
            info=x_info if is_x else ff_info
        )

        if not (is_x or is_ff) and which(binary):
            print(f'[red]Error: [yellow]{binary}[/yellow] cannot be used '
                  f'with [cyan]--bin[/cyan]! Switch to [cyan]--full-args[/cyan].')
            raise Exit(1)

        return line


    def encode(line: str, i: int, name: str, node: VideoNode, res: str) -> None:
        with subprocess.Popen(
            line.format(i=i, name=' ' + name, res=res),
            stdin=subprocess.PIPE,
            stdout=None if verbose else subprocess.DEVNULL,
            stderr=None if verbose else subprocess.DEVNULL,
        ) as process:
            if not verbose:
                print(f'Encoding node {i} ({name})...')

            node.output(cast(BinaryIO, process.stdin), y4m=True)


    available_indices, table = list_available_nodes()

    if available_nodes:
        print('', table)
    else:
        indices = check_indices(available_indices, table)

        Path.mkdir(project_dir / 'clips', exist_ok=True)

        for i, name, node in nodes:
            if i not in indices:
                continue

            line = fullargs if fullargs else get_shell_line()
            try:
                encode(line, i, name, node, res)
            except KeyboardInterrupt:
                # doesn't work well with x264
                raise Abort
            except FileNotFoundError:
                print(f'[red]Error: [yellow]{binary}[/yellow] not in the PATH!')
                raise Exit(1)
            except BrokenPipeError:
                # worked great the other day
                print('[red]Error: Broken pipe!')
                if is_x:
                    print('[red]Make sure your [yellow]x264[/yellow] binary was compiled '
                          'with an MP4 support. Switch to [yellow]FFmpeg[/yellow] if unsure.')
                raise Exit(1)
            except Exception as e:
                print(f'[red]### {e} ###')
                if fullargs:
                    print('[red]Please check the [cyan]--full-args[/cyan] string again.')
                raise Exit(1)
        else:
            if not verbose:
                print('[green]Done!')
