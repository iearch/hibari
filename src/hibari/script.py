import logging
from pathlib import Path

import vapoursynth as vs
from vsview import is_preview, set_output

from jetpytools import mod2
from vstools import (
    Sar,
    change_fps,
    initialize_clip,
    get_framerate,
    get_h,
    get_w,
)

from rich import print
from typer import Exit


script_path = Path(__file__)

nodes_desc = {
    'full clip': 'animated image sequence only',
    'cropped clip': 'clip cropped / bordered by user',
    'vertical': 'clip stacked with a comparison clip vertically',
    'horizontal': 'clip stacked with a comparison clip horizontally',
    'merged': 'two clips merged into one; esp. useful for previewing',
    'bordered clip': 'clip cropped / bordered to the comparison clip dimensions',
    'source clip': 'comparison source, resized to the clip width and trimmed',
    'full source': 'full source; useful for determining the desired frame range'
}


def vsscript(
    ts_name: str,
    quiet: bool,
    resize_val: int | None = None,
) -> list[tuple[int, str, vs.VideoNode]]:
    '''
    A general function to unify all VapourSynth operations and make vsview work
    with a less obnoxious workaround.
    '''
    from hibari.config import (
        user_img_dir,
        what_to_print,
        scale,
        pos,
        crop,
        border_clr,
        stack_with_cropped,
        colors,
        fps_num,
        fps_den,
        comp_src,
        first_frame,
        last_frame,
        comp_filler_start_length,
        comp_filler_end_length,
        start_clr,
        end_clr,
        weight,
        lvl_thr,
        lvl_gamma,
        inscribe,
        invert,
        lsmas,
        l_cachedir,
    )
    from hibari.timesheet import imgseq, file_dict, get_timings_from_timesheet


    timed = get_timings_from_timesheet(ts_name)

    out_names = list[str]()
    out_nodes = list[vs.VideoNode]()
    core = vs.core

    logging.getLogger('vapoursynth').setLevel(logging.ERROR)

    def normalize(clip: vs.VideoNode) -> vs.VideoNode:
        '''
        Provides a proper color transfer to 8-bit 4:2:0 YUV with BT.709 colorimetry.
        '''
        inited_clip = initialize_clip(clip).std.RemoveFrameProps('_Alpha')
        transferred_clip = inited_clip.resize.Bilinear(
            format=vs.YUV420P8,
            matrix_s='709',
            transfer_s='709',
            primaries_s='709',
            range=0,
        )

        return transferred_clip


    def clip_from_images() -> vs.VideoNode:
        '''
        Each image is repeated `n` frames, where `n` is a timing taken from the timesheet.  
        For better performance, bs caches every image in the directory.

        Thanks to myrsloik for <https://forum.doom9.org/showthread.php?p=1792415#post1792415>
        '''
        sample_image = core.bs.VideoSource(user_img_dir / imgseq[0], showprogress=False)
        force_even_dims = core.resize.Lanczos(sample_image,
                                              width=mod2(sample_image.width),
                                              height=mod2(sample_image.height))
        blank_clip = core.std.BlankClip(force_even_dims,
                                        format=vs.RGB24,
                                        length=len(timed),
                                        fpsnum=fps_num,
                                        fpsden=fps_den)

        placeholder_clip = normalize(blank_clip)

        def image_loader(n: int) -> vs.VideoNode:
            name = timed[n][0]
            if name in colors:
                filler_clip = core.std.BlankClip(clip=placeholder_clip,
                                                 color=colors[name],
                                                 format=vs.RGB24)[0]
                return normalize(filler_clip)
            else:
                image_src = core.bs.VideoSource(user_img_dir / file_dict[name],
                                                cachemode=2, showprogress=False)[0]
                image = normalize(image_src)
                return image.resize.Lanczos(placeholder_clip.width, placeholder_clip.height)

        eval_clip = core.std.FrameEval(placeholder_clip, image_loader)

        return eval_clip


    def prepare_comp_source() -> list[vs.VideoNode]:
        def init_source() -> vs.VideoNode:
            try:
                if lsmas:
                    Path.mkdir(l_cachedir, exist_ok=True)
                    src = core.lsmas.LWLibavSource(comp_src, cachedir=l_cachedir)
                else:
                    src = core.bs.VideoSource(comp_src)
            except vs.Error:
                print(f'[red]Error: Couldn\'t open a comparison source:\n'
                      f'[yellow]\'{str(comp_src)}\'')
                raise Exit(1)

            src = normalize(src)

            # resizing to sar 1:1 (more or less) if the source is anamorphic
            src_sar = float(Sar.from_clip(src))
            if src_sar < 1:
                src = src.resize.Lanczos(width=src.width,
                                         height=mod2(src.height / src_sar))
            elif src_sar > 1:
                src = src.resize.Lanczos(width=mod2(src.width * src_sar),
                                         height=src.height)

            user_fps = get_framerate((fps_num, fps_den))
            src_fps = get_framerate(src)
            var_fps_fraction = get_framerate((0, 1))

            if user_fps != src_fps and not quiet:
                print(f'Clip frame rate: {user_fps} ({user_fps:.3f}).\n'
                      f'Comparison source frame rate: {src_fps} ({src_fps:.3f}).')
                if src_fps == var_fps_fraction:
                    print('[red]Warning: Comparison source has variable frame rate!')
                else:
                    print('Currently, comparison source frame rate is changed to ' 
                          'match the set frame rate of a clip (speed is the same). '
                          'You may want to match comparison '
                          'source frame rate instead in the config.')

            return src

        def trim_clip(clip: vs.VideoNode) -> vs.VideoNode:
            try:
                # with None, std.Trim doesn't trim the end
                return clip.std.Trim(first_frame, last_frame if last_frame != 0 else None)
            except vs.Error:
                print('[red]Error: Cannot trim the comparison source! '
                      'Please check trimming settings in the config.')
                raise Exit(1)

        def add_fillers(clip: vs.VideoNode) -> vs.VideoNode:
            if comp_filler_start_length > 0:
                comp_filler_start = clip.std.BlankClip(
                    length=comp_filler_start_length,
                    format=vs.RGB24,
                    color=colors[start_clr]
                )
                filler_clip_s = normalize(comp_filler_start)
                clip = filler_clip_s + clip

            if comp_filler_end_length > 0:
                comp_filler_end = clip.std.BlankClip(
                    length=comp_filler_end_length,
                    format=vs.RGB24,
                    color=colors[end_clr]
                )
                filler_clip_e = normalize(comp_filler_end)
                clip = clip + filler_clip_e

            return clip

        src = init_source()
        src_clip = trim_clip(src)
        src_clip = add_fillers(src_clip)

        return [src, src_clip]


    def border_or_crop_clip(clip: vs.VideoNode) -> vs.VideoNode:
        '''
        Borders or crops clip only if told so by user.
        '''
        crop_dist = [mod2(val) if val >= 0 else 0 for val in crop.values()]
        border_dist = [mod2(abs(val)) if val < 0 else 0 for val in crop.values()]

        clip_crop = clip.std.Crop(crop_dist[0], crop_dist[1], crop_dist[2], crop_dist[3])
        clip_bord = clip_crop.std.AddBorders(border_dist[0], border_dist[1], border_dist[2],
                                             border_dist[3], color=border_clr)
        return clip_bord


    def stack_two_clips(clip1: vs.VideoNode, clip2: vs.VideoNode) -> list[vs.VideoNode]:
        _clip2 = change_fps(clip2, get_framerate(clip1))

        clip2_ver = _clip2.resize.Lanczos(clip1.width, get_h(clip1.width, _clip2, mod=2))
        clip_ver = core.std.StackVertical([clip1, clip2_ver])

        clip2_hor = _clip2.resize.Lanczos(get_w(clip1.height, _clip2, mod=2), clip1.height)
        clip_hor = core.std.StackHorizontal([clip1, clip2_hor])
        
        return [clip_ver, clip_hor]


    def prepare_clips_for_merge(clip1: vs.VideoNode, clip2: vs.VideoNode) -> list[vs.VideoNode]:
        clip2_to_clip1 = clip2.resize.Lanczos(clip1.width, get_h(clip1.width, src, mod=2))
        
        h_dif = abs(clip2_to_clip1.height - clip1.height)
        is_div_by_4 = h_dif % 4 == 0
        if clip2_to_clip1.height >= clip1.height:
            if is_div_by_4:
                bordered = clip1.std.AddBorders(top=h_dif / 2, bottom=h_dif / 2,
                                                color=border_clr)
            else:
                bordered = clip1.std.AddBorders(top=h_dif/2 + 1, bottom = h_dif/2 - 1,
                                                color=border_clr)
        else:
            if is_div_by_4:
                bordered = clip1.std.Crop(top=h_dif / 2, bottom=h_dif / 2)
            else:
                bordered = clip1.std.Crop(top=h_dif/2 + 1, bottom=h_dif/2 - 1)

        return [bordered, clip2_to_clip1]


    def merge_two_clips(clip1: vs.VideoNode, clip2: vs.VideoNode) -> vs.VideoNode:
        _clip2 = change_fps(clip2, get_framerate(clip1))

        clip1_len, clip2_len = clip1.num_frames, _clip2.num_frames
        if clip1_len > clip2_len:
            dif_len = clip1_len - clip2_len
            _clip2 = _clip2 + _clip2[-1]*dif_len

        bordered_lvl = clip1.std.Levels(max_in=lvl_thr, max_out=235,
                                        gamma=lvl_gamma, planes=[0])
        if inscribe:
            if invert:
                bordered_lvl_inv = bordered_lvl.std.Invert(planes=[0])
                merged = core.std.Expr([_clip2, bordered_lvl_inv], ['x y max', ''])
            else:
                merged = core.std.Expr([_clip2, bordered_lvl], ['x y min', ''])
        else:
            merged = _clip2.std.Merge(bordered_lvl, weight)

        return merged


    def text_printer(clip: vs.VideoNode, n: int = 0) -> vs.VideoNode:
        def printer(text: str) -> vs.VideoNode:
            return clip.text.Text(text, alignment=pos, scale=scale)

        def print_by_frame(n: int = 0) -> vs.VideoNode:
            _n = n if n < len(timed) else len(timed) - 1

            name = timed[_n][0]
            timing = timed[_n][1]
            comment = timed[_n][2]
            line = timed[_n][3]
            match what_to_print:
                case 'names':
                    return printer(name) if name not in colors else clip
                case 'full names':
                    return printer(name)
                case 'timings':
                    return printer(timing) if name not in colors else clip
                case 'full timings':
                    return printer(timing)
                case 'comment':
                    return printer(comment)
                case 'lines':
                    return printer(line)
                case '':
                    return clip
                case _:
                    print('[red]Error: Cannot type the text!\n'
                          'Adjust [yellow]what_to_print[/yellow] setting in the config.')
                    raise Exit(1)

        print_by_frame()
        eval_clip = core.std.FrameEval(clip, print_by_frame)

        return eval_clip


    def _set_output(clip: vs.VideoNode, name: str, print_text: bool = True) -> None:
        if resize_val:
            clip = clip.resize.Lanczos(get_w(resize_val, clip, mod=2), mod2(resize_val))

        out_clip = text_printer(clip) if print_text else clip
        set_output(out_clip, name)

        out_names.append(name)
        out_nodes.append(out_clip)


    is_cropped = sum(abs(val) for val in crop.values()) != 0
    is_comp_provided = comp_src != ''

    anim_clip = clip_from_images()
    _set_output(anim_clip, 'full clip')

    clip_crop = border_or_crop_clip(anim_clip)

    if not is_comp_provided:
        _set_output(clip_crop, 'cropped clip') if is_cropped else None
    else:
        src, src_clip = prepare_comp_source()

        clip_ver, clip_hor = stack_two_clips(clip_crop if stack_with_cropped else anim_clip, src_clip)

        bordered, src_to_clip = prepare_clips_for_merge(clip_crop, src_clip)
        merged = merge_two_clips(bordered, src_to_clip)

        is_different_from_clip = (anim_clip.height != bordered.height
                                  or anim_clip.width != bordered.width)

        if is_different_from_clip:
            _set_output(bordered, 'bordered clip')
        _set_output(clip_ver, 'vertical')
        _set_output(clip_hor, 'horizontal')
        _set_output(merged, 'merged')
        _set_output(src_to_clip, 'source clip', print_text=False)
        _set_output(src, 'full source', print_text=False)

    out_indices = range(len(out_nodes))

    return list(zip(out_indices, out_names, out_nodes))


bad_msg = 'Something bad happened!\n' \
    'To see the error description, ' \
    'run again: hibari view\n' \
    'Or, alternatively, undo the changes and reload the script.'

if is_preview():
    from hibari import config, timesheet
    from importlib import reload

    reload(config)
    reload(timesheet)

    ts_name: str = globals()['ts_name']
    quiet: bool = globals()['quiet']

    try:
        vsscript(ts_name, quiet)
    except:
        raise RuntimeError(bad_msg)
