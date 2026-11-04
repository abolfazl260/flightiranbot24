# City image optimization

Archived originals: design-assets/cities/original/
Android optimized copies: android/app/src/main/res/drawable-nodpi/

Run from the repository root:

    python -m pip install Pillow==11.3.0
    python scripts/optimize_city_images.py
    python scripts/optimize_city_images.py --check

Defaults: 512x512, WebP quality 88, LANCZOS resampling, encoder method 4.
Transparency and aspect ratio are preserved (non-square images are padded,
not cropped). Original files are read-only and never modified. Every optimized
image is atomically replaced using the original filename. Missing originals,
unexpected Android city files, excessive output sizes, dimensions and alpha
are checked before success is reported.

Review generated changes in a pull request. Do not bundle archived originals
into any Android sourceSet. Android release builds stay manually triggered.
