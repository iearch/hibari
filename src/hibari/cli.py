import subprocess
from typing import Annotated

from typer import Exit, Option, Typer

from . import __version__ as ver
from .config import init_project, inited_check
from .timesheet import create_timesheet, images_in_directory_check
from .script import script_path, vsscript
from .encode import encode_out_nodes


__all__ = ['app']

app = Typer(
    invoke_without_command=True,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=f'hibari /// animation tool /// v{ver}',
    rich_markup_mode='rich',
    add_completion=False,
)


@app.command(help='Create a config file.')
def init() -> None:
    init_project()


@app.command(help='Create a timesheet.')
def timesheet(
    timing: Annotated[
        int,
        Option(
            '-t',
            '--timing',
            min=1,
            help='Provide a custom timing to be used for each image.',
        )
    ] = 4,
) -> None:
    inited_check()
    images_in_directory_check()

    create_timesheet(timing)
    raise Exit


ts_name_help = 'Read the timesheet from a different file instead of ' \
    '[yellow]./timesheet.txt[/yellow]. File must be in the same directory. ' \
    'Provide a name without an extension.'


@app.command(help='Open VSView for preview.')
def view(
    ts_name: Annotated[
        str,
        Option(
            '-t',
            '--timesheet-name',
            help=ts_name_help,
        )
    ] = 'timesheet',
    quiet: Annotated[
        bool,
        Option(
            '-q',
            '--quiet',
            help='Suppress frame rate information and warnings.',
        )
    ] = False,
) -> None:
    inited_check()
    images_in_directory_check()
    
    # only to properly collect exceptions
    vsscript(ts_name, quiet)

    subprocess.Popen(['vsview', '-a', f'ts_name={ts_name}', '-a', f'quiet={quiet}', script_path],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    raise Exit


@app.command(help='Encode clips with x264, FFmpeg, or another encoder.')
def encode(
    available_nodes: Annotated[
        bool,
        Option(
            '-l',
            '--available-nodes',
            help='List available nodes with a description for each.',
        )
    ] = False,
    node_index: Annotated[
        str,
        Option(
            '-n',
            '--node',
            help='Provide nodes you want to encode. Use '
                 '[cyan]0,3,4[/cyan] for separate nodes and '
                 '[cyan]0..3[/cyan] for ranges.',
        )
    ] = '0',
    resize: Annotated[
        int | None,
        Option(
            '-r',
            '--resize',
            help='Proportionally resize output to the given height.',
        )
    ] = None,    
    ts_name: Annotated[
        str,
        Option(
            '-t',
            '--timesheet-name',
            help=ts_name_help,
        )
    ] = 'timesheet',
    verbose: Annotated[
        bool,
        Option(
            '-v',
            '--verbose',
            help='Show full encoding information.',
        )
    ] = False,
    binary: Annotated[
        str,
        Option(
            '-b',
            '--bin',
            help='Select an encoder. Default arguments are switched as well '
                 'to match the syntax. FFmpeg is libx264-only with this argument. '
                 'Output container is MP4.',
            rich_help_panel='x264 / FFmpeg',
        )
    ] = 'FFmpeg',
    args: Annotated[
        str,
        Option(
            '-a',
            '--args',
            help='Provide arguments passed to the encoder. Colorimetry and output '
                 'are already set up. For resizing, use --resize.',
            rich_help_panel='x264 / FFmpeg',
        )
    ] = '-preset veryslow -crf 13.5',
    fullargs: Annotated[
        str | None,
        Option(
            '-f',
            '--full-args',
            help='Provide a full string passed to the shell. '
                 'Use [cyan]-[/cyan] instead of the input path, '
                 'add [cyan]{i}[/cyan] to the output filename to indicate a node '
                 'index, [cyan]{name}[/cyan] to indicate a node name, and '
                 '[cyan]{res}[/cyan] to indicate the output height (passed with --resize); '
                 'also, choose Y4M demuxer. It is a good practice '
                 'to encode in the [yellow]./clips/[/yellow] subdirectory.',
            rich_help_panel='Other encoders',
        )
    ] = None,
) -> None:
    inited_check()
    images_in_directory_check()

    encode_out_nodes(ts_name, binary, args, node_index, available_nodes, verbose, fullargs, resize)
    raise Exit
