# Local Shazam / Brand kit
## Direction
Monochrome. Precise. Uncluttered. An independent tool for recognizing your own audio.
The paired-corner mark represents two fragments brought into alignment. It is not
the official Shazam symbol; do not imply affiliation with Apple or Shazam.

## Core assets
- Optional standalone hero: [banner](../assets/banner.svg). The README uses a compact, centered, theme-aware mark instead.
- Transparent marks: [black](../assets/brand/mark-black.svg), [white](../assets/brand/mark-white.svg).
- Transparent wordmarks: [black](../assets/brand/wordmark-black.svg), [white](../assets/brand/wordmark-white.svg).
- Square icon tiles: [black mark / white tile](../assets/brand/icon-black.svg),
  [white mark / black tile](../assets/brand/icon-white.svg).
- Machine-readable design values: [tokens](../assets/brand/tokens.json).

SVGs are editable production sources. Wordmarks use live system text with Arial,
Helvetica and sans-serif fallbacks; they are not font-outlined masters.
Icon artwork is provided here, not embedded into the existing executable.

## Color and typography
Only #000000 and #FFFFFF. Use full contrast and negative space rather than
gradients, shadows, colored accents or decoration.
Arial Bold for display and wordmark; Arial Regular for explanatory copy.
Lowercase the visual wordmark; use **Local Shazam** in prose.
Use an 8-unit layout rhythm. Keep supporting copy substantially smaller than the headline.

## Mark rules
Keep at least 24 units of clear space around the 96-unit mark.
Minimum standalone size: 16 pixels. Use the mark alone at small sizes.
Do not stretch, rotate, add effects, round the corners or reconstruct the geometry.
White artwork is for black backgrounds; black artwork is for white backgrounds.

## Voice
Short, plain and confident. Lead with what the user can do, not the implementation.
Headline: **Your library. Recognized.**
Supporting line: **Private by design. Local by default.**
Never promise universal recognition, 100% accuracy or guaranteed matches.
Keep install requirements, experimental status and confidence limitations in product docs.

## Design provenance
The initial identity board was explored with the built-in image-generation tool.
The final SVG system was authored separately as deterministic vector geometry.
The local concept preview is in dist/brand/brand-direction.png (not a release artifact).
The exact exploration prompt is in BRAND-PROMPT.txt. No generated image is required
to render the README. This branding pass does not modify runtime behavior or packages.
