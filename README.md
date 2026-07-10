# hibari

This small command line tool lets you create clips from individual images with a specified repeat number (timing) for each image, using a plain text timesheet. In addition, it is possible to create a comparison by stacking a comparison clip either vertically or horizontally, or merging two clips into one.

`hibari` was originally written for animating production materials where timings are unknown but a final video is available and can be used as a guide.

Made courtesy of [VapourSynth](https://github.com/vapoursynth/vapoursynth) and [VSView](https://github.com/Jaded-Encoding-Thaumaturgy/vs-view).

## Installing

- install [Python](https://www.python.org/downloads/)
- config the PATH, if not yet
- run in the terminal:
    ```
    pip install hibari
    ```
- for encoding, install `x264` (MP4 support is required) or `FFmpeg` in the PATH

## Usage

To initiate a project, run in a directory:
```
hibari init
```
`hibari` works by loading all the images from a subdirectory called `images`, loading each line from a timesheet located in the project directory, checking if all lines match images, and then repeating each image by a corresponding timing.

See the config file for the full available options.

Also, see a [sample project](./src/hibari/sample_project/) for a directory structure if in doubt.

### Images

Images are loaded in the order they appear in a default file manager in your OS.

Maintaining the same resolution or format is not required, but it is recommended that images have at least a similar aspect ratio to avoid stretching.

If an image name ends with `#`, it is ignored. With a large number of images you want `hibari` to ignore, move them in another subdirectory instead.

### Timesheet

Once images are placed in the corresponding directory, run:
```
hibari timesheet
```
This will create a simple timesheet. Timesheet template can be found [here](./src/hibari/sample_project/timesheet.txt).

In addition to image names, you can also write a color name with a desired timing to add a color filler. Color names are predefined in the config file and can be easily adjusted.

If you want to have several timesheets for different purposes, copy the timesheet, edit it, and pass its name with `--timesheet-name` option:
```powershell
hibari view --timesheet-name 'ts alt'
```
Then `hibari` will try to find `ts alt.txt` in the project directory instead of `timesheet.txt`.

### Comparison clip

To load a comparison clip, enter its path in the config file, and match frame rate if needed.

### View

By running `hibari view`, you will only see one clip available, but cropping it or loading a comparison clip will spawn other clips (called *nodes*).

Shortcuts for `VSView`:
- `Ctrl+R` for reloading the script and viewing changes made to the project
- left / right arrows for framestepping (holding down `Shift` increases a step)
- numeric keys for switching between nodes

### Encode

To encode the nodes, you need to have at least one encoder in the PATH. `x264` and `FFmpeg` have default settings and syntax in `hibari`, but passing stdout to another encoder is possible as well.

To use `FFmpeg` with another encoder besides `libx264`, check `--full-args` option. 

Encode a range of nodes with default settings:
```powershell
hibari encode -n 0..6
```

Switch to `x264` and custom arguments:
```powershell
hibari encode --bin x264 --args '--crf 14 --no-mbtree --qpstep 2 --aq-mode 2 --aq-strength 0.95 --qcomp 0.65' -n 0,4
```

Switch to another encoder and resized output:
```powershell
hibari encode --full-args 'ffmpeg -y -i - -c:v libx265 -preset veryslow -crf 12 -x265-params "colormatrix=bt709:transfer=bt709:colorprim=bt709" "./clips/{i}{name}{res}.mp4"' --resize 480 -n 4
```
Where:
- `{i}` is a node index
- `{name}` is a node short name
- `{res}` is an output height; you can safely add it even if `--resize` option has not been used, as it will yield an empty string instead