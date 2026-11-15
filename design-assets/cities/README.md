# City artwork assets

`original/` contains the source WebP city illustrations. The initial 56 images were copied byte-for-byte from `android/app/src/main/res/drawable-nodpi/price_city_*.webp` at commit `6a330b1aa89499a6b9e79ba0565c9b24c3188f49`, preserving their Git blob SHA identities. Four additional high-resolution city illustrations (Shahrekord, Lamerd, Kandahar and Tashkent) were archived on 2026-11-15; their optimized copies are placed in `drawable-nodpi`. Total: 60 cities.

**Do not include this directory in the Android app's source sets.** The Android `drawable-nodpi` directory contains lightweight 512x512 WebP replacements. The archived originals are the source of truth for future conversions. Preserve alpha channel, proportions and filenames, and verify UI quality before changing Android resources.
