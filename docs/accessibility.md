# Accessibility

Lumia aims at RGAA 4.1 level AA (which maps to WCAG 2.1 AA). This page says what is checked
automatically, what is only checked by hand, and what is known not to be conformant.

## Conformance declaration

**Partially conformant.** No third-party audit has been done. The statement rests on automated checks
plus the manual review done while writing this page.

- Automated: axe-core (WCAG 2.0/2.1 A and AA rules) runs on ten screens in light and dark theme
  (`apps/web/e2e/accessibility.spec.ts`, part of the CI e2e job). It covers what a machine can detect,
  roughly a third of the RGAA criteria; a green run is not a claim of full conformance.
- Not formally verified: screen-reader behaviour (NVDA, JAWS, VoiceOver), reflow at 200% and 400% zoom
  on every screen, text-spacing overrides, the audio player with assistive technology, and the article
  body (third-party HTML sanitised upstream, so its images, tables and heading order depend on the
  source).
- Screens not scanned: login, onboarding, reset-password, article detail, playlist detail, share.

## Keyboard

Everything reachable with a pointer is reachable with the keyboard. A "skip to content" link is the
first stop, the focus ring is visible, dialogs trap focus and give it back on close.

Global shortcuts are listed by pressing `?`. They are disabled while typing in a field or while a
dialog or menu is open.

### Spark mode (swipe alternative)

| Gesture      | Key         | Button     |
| ------------ | ----------- | ---------- |
| Swipe right  | Right arrow | Like       |
| Swipe left   | Left arrow  | Dislike    |
| Swipe up     | Up arrow    | Favourite  |
| Swipe down   | Down arrow  | Read later |
| Tap the card | -           | Open       |

When the summary text has focus, Up and Down scroll it instead of voting. The result of every action
is announced in a polite live region ("Like: <title>"), then the next article is announced.

### Flip reader (page-turn alternative)

`ArrowRight` or `j` goes to the next page, `ArrowLeft` or `k` to the previous one, `Escape` closes.
The Previous and Next buttons do the same. The position is announced on every turn and focus returns
to the element that opened the reader.

## Motion

`prefers-reduced-motion: reduce` collapses CSS animations and transitions to a near-instant state, and
the programmatic scrolling of the read-aloud highlight and of the highlight reveal switches from smooth
to instant. The karaoke highlight is a colour change, not a movement, so it stays on.

## Colour and contrast

Axe checks text contrast in both themes. The muted text token and the accent colour are tuned so muted
text and accent text on tinted backgrounds reach 4.5:1. Already-read article cards dim their picture
rather than their text, because dimmed text falls below the threshold.

## Known gaps

- Third-party article HTML is displayed as received.
- The audio player and the highlights have not been tested with a screen reader.
- Accent hues other than the default have not each been measured.

## Reporting a problem

Open an issue with the screen, the assistive technology and the browser.
