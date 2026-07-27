# UI-ALIGN-003 — ASIE Complete Frontend Surface Package

Status: IMPLEMENTED ON FEATURE BRANCH — CI REQUIRED BEFORE MERGE  
Date: 2026-07-27  
Scope owner: Frontend presentation layer only

## 1. Purpose

This package completes the approved ASIE visual alignment in one consolidated delivery instead of splitting landing, dashboard, authentication, project stages, reports, settings, admin, and DIB routes across multiple small pull requests.

The approved visual reference is the light institutional Arabic-first model provided for the project. Its fixed palette is:

```text
Background          #F5F7F3
Secondary background #EDF2EB
Card                #FFFFFF
Secondary surface   #F4F7F2
Brand green         #12805C
Dark green          #0B6246
Amber emphasis      #D97706
Teal success        #0D9488
Primary text        #102B21
Secondary text      #46574E
Muted text          #7D8C83
```

Dark themes, purple/cyan startup gradients, neon effects, and unrelated visual palettes are not part of this package.

## 2. Delivered surfaces

### Public surface

- Existing ASIE landing hero and navigation restyled under the approved palette.
- Complete public navigation: How it works, capabilities, Sanad, usage tracks, and FAQ.
- Capability cards limited to supported or explicitly governed ASIE behavior.
- Sanad presented as a local navigation and guidance interface; no external AI provider or expert-review promise is implied.
- Usage tracks replace unapproved live prices or payment claims.
- FAQ states current file and network boundaries honestly.
- Final call to action and platform footer.

### Authentication and legal surface

- Login, first bootstrap, recovery, and legal acceptance use one centered institutional card system.
- Local security and recovery messages remain unchanged.
- No authentication flow or tenant-isolation behavior is modified.

### Authenticated client workspace

- White sidebar and pale workspace shell.
- Approved green active navigation and restrained amber emphasis.
- A complete ASIE page hub exposing the approved page architecture:
  - لوحة القيادة
  - مرشد تأسيس المشروع
  - طبقة الأدلة
  - جاهزية الدراسة
  - تشغيل التحليل
  - اختبر السوق
  - فهم القرار
  - خارطة التنفيذ
  - تقاريري
- The hub activates existing live stages; it does not calculate or persist data.
- Shared cards, tables, stage rails, forms, status states, progress indicators, wizard blocks, evidence, readiness, decision, execution, and reports receive one design language.

### Sanad workspace assistant

- A visible local guidance launcher appears inside the authenticated workspace.
- It navigates to project definition, evidence, and decision pages.
- It does not call an API, generate financial numbers, enable an AI provider, or bypass ASIE gates.

### Admin and DIB routes

- Admin login, metrics, organization/user panels, and health views use the approved palette.
- DIB standalone routes use the same card, form, action, and status language.
- Existing DIB API behavior and forbidden boundaries remain unchanged.

### Responsive and accessibility

- Desktop, tablet, and mobile layouts are included in the same package.
- Reduced-motion preferences are respected.
- Focus-visible styling is centralized.
- Contrast is based on the approved dark-green text over pale or white surfaces.

## 3. Implementation files

```text
src/ASIECompleteSurfaceMount.tsx
src/asie-complete-surface.css
src/main.tsx
tests/test_ui_complete_frontend_surface_package.py
```

Import order is mandatory:

```text
styles.css
asie-reference-theme.css
asie-complete-surface.css
```

The complete surface stylesheet must remain last so it can normalize legacy and route-specific styles without editing runtime components.

## 4. Capability honesty

This package does not silently turn planned functionality into implemented functionality.

The landing and FAQ explicitly state:

- Manual, CSV, and XLSX intake are the current live file paths.
- PDF intake and supplier-quote extraction remain planned until implemented and admitted.
- External market fetch and AI providers are disabled in the current local mode.
- Finance calculations remain deterministic.
- Pricing and external payment claims are not presented as active commerce.

## 5. Hard boundaries

This package must not modify:

- AAS Runtime Freeze files.
- Backend APIs or contracts.
- DIB persistence, validation, or runtime wiring.
- Finance calculations.
- Snapshot assembly or lineage.
- Decision Council logic.
- AI-provider or external-network behavior.
- Authentication, authorization, or tenant isolation.

## 6. Verification

The static package guard verifies:

- Exact palette tokens.
- Final import order.
- Coverage of landing, auth, legal, workspace, wizard, evidence, decision, execution, snapshots, DIB, admin, responsive, and reduced-motion surfaces.
- Presence of the approved ASIE page map.
- Honest statements about PDF, AI provider, network, and payment limitations.
- Absence of API/runtime imports from the surface mount.
- AAS frozen runtime integrity.

Merge is allowed only after frontend build, backend compile, and Python tests succeed in GitHub Actions.

## 7. Completion rule

After this package is merged, visual page alignment is treated as one completed baseline. Later page changes must be driven by a concrete missing workflow, accessibility defect, responsive defect, or approved product requirement—not by repeated cosmetic micro-PRs.
