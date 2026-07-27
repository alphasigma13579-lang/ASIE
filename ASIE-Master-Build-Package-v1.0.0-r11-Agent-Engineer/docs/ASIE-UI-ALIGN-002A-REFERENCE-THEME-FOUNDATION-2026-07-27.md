# ASIE UI-ALIGN-002A — Reference Theme Foundation

Status: IMPLEMENTED ON FEATURE BRANCH
Date: 2026-07-27
Scope: Landing page and authenticated application shell visual foundation

## Decision

The approved visual reference is the light institutional ASIE interface supplied as the landing-page and dashboard HTML references.

The canonical palette is:

- Background: `#F5F7F3`
- Secondary background: `#EDF2EB`
- Card: `#FFFFFF`
- Secondary card: `#F4F7F2`
- Border: `#DFE6DB`
- Soft border: `#E7ECE2`
- Primary green: `#12805C`
- Dark green: `#0B6246`
- Amber accent: `#D97706`
- Teal status: `#0D9488`
- Danger: `#DC2626`
- Primary text: `#102B21`
- Secondary text: `#46574E`
- Muted text: `#7D8C83`

Dark, neon, cyan-purple, and glassmorphism themes are not approved for the ASIE primary product interface.

## Implemented in this package

1. Added `src/asie-reference-theme.css` as a separate visual layer.
2. Loaded it after the legacy stylesheet so the approved palette becomes authoritative without deleting existing component rules.
3. Restyled the existing landing structure into the approved light hero, dashboard-preview card, service ribbon, and decision-flow cards.
4. Restyled the authenticated shell into the approved white sidebar, pale background, green active states, white cards, and restrained amber emphasis.
5. Added a static test protecting the exact approved tokens and import order.

## Hard boundaries

This package does not modify:

- API calls or endpoint behavior
- AAS Runtime Freeze files
- DIB contracts or runtime wiring
- Finance calculations
- Snapshot assembly or projections
- AI providers or network policy
- Authentication, organization isolation, or permissions

## Next implementation package

`UI-ALIGN-002B — Landing Content and Navigation Completion`

It should complete the approved landing navigation and page sections while retaining the existing product-entry and authentication gates.

After that:

`UI-ALIGN-002C — Dashboard Information Architecture Adoption`

It should map the approved dashboard structure to the live stages and data contracts without introducing simulated values as live data.
