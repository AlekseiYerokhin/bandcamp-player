---
description: Build the AppImage
agent: build
---

Build the AppImage from the repository root:

```bash
./packaging/build-appimage.sh
```

The output lands at `build/Bandcamp-Player-x86_64.AppImage`. Report the final
size. If the build or the resulting AppImage misbehaves, consult the
`build-appimage` skill and the gotchas in AGENTS.md before changing
`bandcamp.spec`, `packaging/build-appimage.sh`, or `packaging/AppDir/AppRun`.