# Third-party notices

UmbraForge's own source code is licensed under the MIT Licence. See
[`LICENSE`](LICENSE).

The Windows releases bundle the libraries below. They are used unmodified and
keep their own licences. Full licence texts for the GNU licences are in
[`licenses/`](licenses/).

## Bundled at runtime

| Component | Version | Licence | Project |
|---|---|---|---|
| Qt for Python (PySide6, Shiboken6, Qt libraries) | 6.12.0 | LGPL-3.0-only (also offered by The Qt Company under GPL and commercial terms) | <https://pypi.org/project/PySide6/> · <https://www.qt.io/licensing/open-source-lgpl-obligations> |
| Pillow | 13.0.0 | MIT-CMU (HPND) | <https://python-pillow.org/> |
| NumPy | 2.5.4 | BSD-3-Clause | <https://numpy.org/> |
| Python runtime | 3.13 | PSF-2.0 | <https://www.python.org/> |

Qt itself embeds further third-party components (for example ICU, zlib and
image codecs). Their notices ship with the Qt source distribution at
<https://download.qt.io/official_releases/qt/>.

## Build tooling (not distributed inside the portable app)

| Component | Version | Licence |
|---|---|---|
| PyInstaller | 6.22.3 | GPL-2.0-or-later with the PyInstaller bootloader exception, which permits distributing bundled applications under their own licence |

## Optional, not part of the standard release

| Component | Licence | Project |
|---|---|---|
| rembg | MIT | <https://github.com/danielgatis/rembg> |
| onnxruntime | MIT | <https://onnxruntime.ai/> |

AI cutout is only available when the user installs these packages; the release
does not include them and the app works fully without them.

## LGPL compliance

PySide6 and the Qt libraries are distributed under the GNU Lesser General
Public Licence, version 3. The release keeps them as separate, unmodified
shared libraries inside the application folder/exe payload.

UmbraForge's complete source, build script and packaging metadata are published
in this repository. You may rebuild the application against your own build of
Qt/PySide6 by installing a different PySide6 version and running:

```powershell
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\python.exe tools\build_release.py
```

Source code for the LGPL components is available from the upstream projects
linked above (PyPI publishes the corresponding source distributions).

## Fonts

UmbraForge uses fonts already installed on the user's machine. No font files
are redistributed with the application.
