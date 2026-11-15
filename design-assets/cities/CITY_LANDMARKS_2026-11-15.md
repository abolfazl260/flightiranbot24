# Additional city artwork — 2026-11-15

Four 3D diorama illustrations added for the ticket-price destination list:

| Persian city | Resource | Intended visual reference |
| --- | --- | --- |
| شهرکرد | `price_city_shahrekord.webp` | Chaleshtar historic Qajar mansion and Zagros landscape |
| لامرد | `price_city_lamerd.webp` | Chalehgah rock-cut heritage site and southern Fars landscape |
| قندهار | `price_city_kandahar.webp` | Shrine of the Cloak (Khirqah Sharif) |
| تاشکند | `price_city_tashkent.webp` | Kukeldash Madrasah |

These are **stylized AI-generated illustrations**, not documentary or exact architectural reconstructions. They use the existing city illustration visual language.

Each resource has two copies with the same basename:
- Source archive: `design-assets/cities/original/` — 1254x1254 transparent WebP, not shipped in Android.
- Runtime asset: `android/app/src/main/res/drawable-nodpi/` — 512x512 transparent WebP (quality 88).

City name mapping is defined by `fareCityIconName` in `TicketPricesActivity.kt` and covered by `TicketCityIconMappingTest.kt`.
Run `python scripts/optimize_city_images.py --check` after downloading the branch; it validates all 60 city pairs. Preserve the original images and the bottom navigation UI.
