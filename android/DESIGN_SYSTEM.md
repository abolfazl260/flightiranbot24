# Advertio Android UI contract

Issue: [#64](https://github.com/abolfazl260/flightiranbot24/issues/64)

The Android app is **Persian-only and RTL**, regardless of system language. Do
not add Android locale pickers or separate English/Arabic UI or LTR screens.
IATA codes, airline codes, and URLs may appear as data; they do not change the
root layout direction.

## One palette for Compose + Java/XML

Colors live in `app/src/main/res/values/colors.xml`. Compose reads the same
resources in `presentation/theme/TravelTheme.kt`. The Java checklist uses
`Theme.FlightIran`, `AdvertioHeadline`, `AdvertioBody`, `ChecklistItem`,
and `ServiceButton` styles. Do not define a second hexadecimal palette in
Kotlin or in another Android screen. Spacing and minimum touch sizes live in
`TravelTokens`; Android XML widgets have 56dp minimum rows/actions.

A verified system `sans-serif` font with Android's Persian fallback is used
until an original licensed Advertio font file can be provided. Text sizes are
`sp`, heights are flexible, and dialogs/list rows must not clip at 200%
system font scaling. Icons that are only decorative are hidden from TalkBack.

Reusable Compose components live in
`presentation/components/TravelComponents.kt`. They cover navigation, service
cards, toolbar, form fields, airport rows, empty/loading/error, and confirmation.
Android Studio previews `PreviewSmall` (320dp) and `PreviewLarge` (420dp)
allow visual inspection of Persian spacing on both device classes.

## Branding blocker

The repo does not contain a verifiable **original Advertio logo** or permission
to reconstruct it. The existing launcher graphic is left untouched on purpose.
Before replacing it, obtain the authorized vector or lossless source asset from
the brand owner and create proper `mipmap-anydpi-v26` adaptive icon resources,
foreground, background, and round launcher variants. Check masking on both
round and squircle launchers and verify Play Store assets against the real
master. Do not synthesize a trademark by tracing a screenshot.

## QA checklist before closing #64

- [x] Compose + Java/XML use resource-backed color tokens and RTL conventions.
- [x] Reusable native controls and small/large Persian Compose previews.
- [x] Automated WCAG AA normal-text color combinations and clickable cards.
- [ ] Original licensed launcher logo/adaptive icon supplied and integrated.
- [ ] Manually inspect previews, screenshots, and actual device layout at 320dp
      and 420dp, at normal and 200% font scale.
- [ ] Manually navigate every action with TalkBack, keyboard/D-pad, and focus
      indicators; check error/loading dialogs and empty list announcements.
- [ ] Validate visual contrast and pixel-level consistency on device.

CI can validate compilation, lint, unit checks and screenshot capture; it does
not substitute for the physical-device review above.
