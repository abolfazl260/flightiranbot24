# City artwork assets

`original/` contains the original, unmodified WebP city illustrations. Each file is copied byte-for-byte from `android/app/src/main/res/drawable-nodpi/price_city_*.webp` at commit `6a330b1aa89499a6b9e79ba0565c9b24c3188f49`. Git blob SHA identities are preserved.

**Do not include this directory in the Android app's source sets.** The Android `drawable-nodpi` directory currently retains the originals until independently validated lightweight 512x512 WebP replacements are generated. Archive is the source of truth for future conversions. Preserve alpha channel, proportions and filenames, and verify UI quality before changing Android resources.
