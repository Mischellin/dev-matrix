"""Semantic regression suite for the DevMatrix leaderboard page (``web/index.html``).

Scope
-----
Accessibility / mobile-first **DOM contract** for the single-page frontend.
The page is one hand-written HTML file with an inline ``<script>``; the suite
therefore parses it with the standard library only (``html.parser``) — no
``package.json``, no bundler, no new dependency, no CI change.

**This is NOT a visual / E2E verification.** It proves that the markup exposes
the agreed semantics (names, roles, states, relationships). It cannot prove
layout, absence of horizontal overflow, focus trapping, Escape handling or
runtime behaviour. Those remain the responsibility of the browser probe
(Playwright) and of the implementer's manual QA.

DOM contract (agreed with the frontend implementer)
---------------------------------------------------
The implementer MUST satisfy the following. Ids marked "(agreed id)" are the
ids this suite looks for; they may be introduced by this change.

1. Search input
   * ``#model-search`` is an ``<input>`` with an accessible name provided by
     one of: a ``<label for="model-search">`` with non-empty text, a non-empty
     ``aria-label``, or ``aria-labelledby`` pointing at an element that really
     exists in the markup and has non-empty text.
   * A ``placeholder`` is not an accessible name.

2. Selection groups (role / domain / dataset version)
   * The three groups keep their ids: ``#role-tabs``, ``#domain-filters``,
     ``#version-tabs``.
   * Each group container is ``role="group"`` and has an accessible name
     (``aria-label`` or ``aria-labelledby`` -> existing element with text).
   * Each group is **not** a ``role="tablist"``: a tablist without a complete
     keyboard implementation (arrow keys, roving tabindex) is worse than a
     plain group of toggle buttons.
   * Every button in a group carries ``aria-pressed``. Exactly one button per
     group has ``aria-pressed="true"`` — the one that is initially selected —
     and every other button has ``aria-pressed="false"``.
   * "Initially selected" is the selection the app itself starts with, i.e.
     the values of the page state constants ``currentRole`` / ``currentDomain``
     / ``DEFAULT_VERSION``. The pressed button must be the same one that
     carries the active visual treatment, so the visual state and the
     announced state can never contradict each other.
   * The script must keep ``aria-pressed`` in sync when the selection changes
     (the click handlers that toggle the visual state must update it too),
     otherwise the announced state goes stale after the first interaction.
     The suite only checks that the script *references* ``aria-pressed`` —
     this is a **smoke reference**; the actual state sync is a runtime
     (browser) assertion, not a static one.
   * Cross-check: the button announced as pressed must be the one that carries
     the **current design's active-state marker** (Tailwind classes
     ``bg-indigo-600`` / ``bg-indigo-500/20``, matched as exact class tokens).
     Those markers are *style specific*: if the palette changes, update
     ``ACTIVE_CLASS_MARKERS`` in this file together with this docstring — the
     check fails loudly instead of being skipped.

3. Matrix "Inspect" control
   * ``renderMatrix()`` must render a **real** ``<button>`` carrying
     ``data-model-id="<model id>"`` (either as a template literal or via
     ``document.createElement('button')``).
   * A hybrid is acceptable: a template ``<button>`` that is looked up
     afterwards and stamped with ``btn.dataset.modelId = ...``.
   * The button must have an accessible name (visible text or ``aria-label``).
   * A click-only ``<tr onclick=...>`` with a decorative ``Inspect ->`` span is
     NOT acceptable: the control has to be focusable and announced.

4. Modal
   * ``#modal`` has ``role="dialog"`` and ``aria-modal="true"``.
   * ``#modal`` has ``aria-labelledby`` pointing at a **real heading**
     (``h1``-``h6``) that exists in the static markup and has non-empty text
     (e.g. ``<h2 id="modal-title">`` inside the dialog).
   * ``#modal-close`` is a ``<button>`` with a human-readable accessible name
     (a bare glyph such as ``✕`` is not an accessible name).

5. Scrollable regions
   * Two named, focusable scroll regions (agreed ids):
     ``#matrix-scroll`` and ``#submissions-scroll``.
   * Each: ``tabindex="0"``, ``role="region"``, an accessible name
     (``aria-label`` or ``aria-labelledby`` -> existing element with text) and
     ``aria-describedby`` pointing at an element with real, non-empty hint
     text (e.g. "Scroll horizontally to see all columns").
   * The matrix ``<table>`` lives inside ``#matrix-scroll``; the submissions
     ``<table>`` is rendered into the **stable** ``#submissions-container``,
     which must live inside ``#submissions-scroll``. How the script looks the
     container up (``getElementById``, ``querySelector``, ...) is irrelevant,
     but the id itself is not optional.
   * Both tables survive the refactor (matrix table stays a ``<table>`` with
     its ``<thead>``; the submissions table stays a ``<table>``, not a card
     list).

6. Navigation
   * The page exposes a ``<nav>`` landmark with an accessible name
     (``aria-label`` / ``aria-labelledby``).
   * ``#primary-navigation`` exists and holds the in-page section links
     (at least two ``<a href="#...">``).
   * ``#mobile-nav-toggle`` is a ``<button>`` with ``aria-expanded="false"``
     (collapsed by default), ``aria-controls="primary-navigation"`` and a
     human-readable accessible name.

7. Preserved (must NOT regress)
   * Both dataset paths of ``DATASET_VERSIONS`` survive:
     ``data/benchmark_runs-1.0.0.json`` -> v1.0.0 and
     ``data/benchmark_runs.json`` -> v1.1.0; both files still exist and parse.
   * The version switcher still offers ``1.0.0`` and ``1.1.0``.
   * The version selector keeps its meaning: the matrix keeps showing static
     ratings, the version control only switches the *actual runs* dataset.
     This suite deliberately asserts nothing about concrete ratings, model
     counts or score values.

Implementation notes
--------------------
* Only ``pathlib`` / ``re`` / ``json`` / ``html.parser`` are used.
* JS functions are located by their **declaration** (never by line numbers, so
  inserting lines in the page does not break the suite). Supported forms:
  ``function name(...)`` / ``async function name(...)`` declared at the
  script's base indentation level; the slice ends at that function's own
  closing brace. This is a **text scan of the inline script** — it is not a
  JavaScript parser and it never executes the page's JS.
* Everything asserted here is **static DOM / source smoke**: it proves the
  markup exposes the agreed semantics. It does not prove runtime behaviour
  (state sync after a click, focus trap, Escape, overflow, layout). Those
  belong to the browser probe.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "web" / "index.html"

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# Tailwind classes that mark the *visually* selected button of a group.
# STYLE SPECIFIC to the current design — matched as exact class tokens.
# If the palette changes, update this tuple together with the docstring.
ACTIVE_CLASS_MARKERS = ("bg-indigo-600", "bg-indigo-500/20")

# State constants that define the initial selection of each group.
# Aliases are accepted so a rename does not silently break the contract.
INITIAL_SELECTION_CONSTANTS = {
    "role": ("currentRole", "current_role", "activeRole", "initialRole"),
    "domain": ("currentDomain", "current_domain", "activeDomain", "initialDomain"),
    "version": ("DEFAULT_VERSION", "defaultVersion", "default_version", "INITIAL_VERSION"),
}


# --------------------------------------------------------------------------- #
# Minimal DOM model
# --------------------------------------------------------------------------- #
class Node:
    """One element of the parsed page."""

    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag: str, attrs: list[tuple[str, str | None]], parent: "Node | None"):
        self.tag = tag
        self.attrs = {k.lower(): (v if v is not None else "") for k, v in attrs}
        self.children: list["Node | str"] = []
        self.parent = parent

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<{self.tag} {self.attrs}>"


class PageParser(HTMLParser):
    """Tiny DOM-ish parser: enough for id/attr/tree queries."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", [], None)
        self.current = self.root

    def handle_starttag(self, tag: str, attrs) -> None:
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in VOID_TAGS:
            self.current = node

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.current.children.append(Node(tag, attrs, self.current))

    def handle_endtag(self, tag: str) -> None:
        node = self.current
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None and node.parent is not None:
            self.current = node.parent

    def handle_data(self, data: str) -> None:
        self.current.children.append(data)


class Page:
    """Parsed page + raw script sources."""

    def __init__(self, source: str) -> None:
        self.source = source
        parser = PageParser()
        parser.feed(source)
        parser.close()
        self.root = parser.root
        self.scripts = [node_text(n) for n in iter_nodes(self.root) if n.tag == "script"]
        self.script = "\n".join(self.scripts)

    def function_body(self, name: str) -> str:
        """Text of one top-level JS function, located by its declaration.

        This is a **text scan of the inline script** — it is not a JavaScript
        parser and it never executes the page's JS.

        Supported declaration forms (everything else is out of scope and
        yields an empty string, which the caller must treat as "not found"):

        * ``function name(...)`` and ``async function name(...)``;
        * declared at the script's *base indentation level* (the indentation of
          the declaration itself is used, so 2-space, 4-space and tab indented
          scripts all work);
        * the function ends at the closing brace that sits on that same base
          indentation level.

        The slice therefore stops at the function's own closing brace instead
        of running to the end of the script, and it never bleeds into the next
        top-level declaration.
        """
        decl = re.compile(
            rf"^(?P<indent>[ \t]*)(?:async\s+)?function\s+{re.escape(name)}\s*\(", re.MULTILINE
        )
        match = decl.search(self.script)
        if match is None:
            return ""

        indent = match.group("indent")
        start = match.start()
        pos = start
        while pos <= len(self.script):
            newline = self.script.find("\n", pos)
            line_end = len(self.script) if newline == -1 else newline
            line = self.script[pos:line_end]
            line_indent = line[: len(line) - len(line.lstrip())]
            if pos > start and line_indent == indent:
                stripped = line.strip()
                if stripped == "}":
                    # the function's own closing brace -> the real end
                    return self.script[start:line_end]
                if stripped and not stripped.startswith("}"):
                    # the next top-level statement -> the real end
                    return self.script[start:pos]
            pos = line_end + 1
        return self.script[start:]


_PAGE: Page | None = None


def page() -> Page:
    """Parsed page, parsed once per test session."""
    global _PAGE
    if _PAGE is None:
        _PAGE = Page(PAGE.read_text(encoding="utf-8"))
    return _PAGE


# --------------------------------------------------------------------------- #
# DOM helpers
# --------------------------------------------------------------------------- #
def iter_nodes(node: Node):
    for child in node.children:
        if isinstance(child, Node):
            yield child
            yield from iter_nodes(child)


def find_by_id(root: Node, node_id: str) -> Node | None:
    for node in iter_nodes(root):
        if node.attrs.get("id") == node_id:
            return node
    return None


def find_all(root: Node, tag: str | None = None, **attrs: str) -> list[Node]:
    found = []
    for node in iter_nodes(root):
        if tag is not None and node.tag != tag:
            continue
        if all(node.attrs.get(key) == value for key, value in attrs.items()):
            found.append(node)
    return found


def node_text(node: Node) -> str:
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
        else:
            parts.append(node_text(child))
    return "".join(parts)


def is_descendant(node: Node, ancestor: Node) -> bool:
    parent = node.parent
    while parent is not None:
        if parent is ancestor:
            return True
        parent = parent.parent
    return False


def accessible_name(node: Node, root: Node) -> str:
    """Best-effort accessible name computation (subset of the accname spec).

    Supports: aria-label, aria-labelledby (existing elements only),
    <label for=...> for form controls, title, and text content for
    buttons/links.
    """
    label = node.attrs.get("aria-label", "").strip()
    if label:
        return label

    labelled_by = node.attrs.get("aria-labelledby", "").strip()
    if labelled_by:
        chunks = []
        for ref in labelled_by.split():
            target = find_by_id(root, ref)
            if target is not None:
                text = node_text(target).strip()
                if text:
                    chunks.append(text)
        joined = " ".join(chunks).strip()
        if joined:
            return joined

    if node.tag in {"input", "select", "textarea"}:
        node_id = node.attrs.get("id")
        if node_id:
            for label_node in find_all(root, "label"):
                if label_node.attrs.get("for") == node_id:
                    text = node_text(label_node).strip()
                    if text:
                        return text

    title = node.attrs.get("title", "").strip()
    if title:
        return title

    if node.tag in {"button", "a"}:
        text = node_text(node).strip()
        if text:
            return text

    return ""


def has_letter(text: str) -> bool:
    """A name must contain at least one letter to be human-readable."""
    return any(char.isalpha() for char in text)


def initial_selection(script: str, kind: str) -> str:
    """Initial selection value declared by the page state constants."""
    for name in INITIAL_SELECTION_CONSTANTS[kind]:
        match = re.search(rf"\b{name}\s*=\s*['\"]([^'\"]+)['\"]", script)
        if match:
            return match.group(1)
    raise AssertionError(
        f"the page script must declare the initial {kind} selection "
        f"(one of {INITIAL_SELECTION_CONSTANTS[kind]})"
    )


def has_class(node: Node, class_name: str) -> bool:
    """Exact class-token membership.

    Token based, not substring based: ``hover:bg-indigo-500/20`` must not be
    mistaken for ``bg-indigo-500/20``.
    """
    return class_name in node.attrs.get("class", "").split()


def visually_active(buttons: list[Node]) -> list[Node]:
    """Buttons carrying one of the current active-state style markers.

    The markers are **style specific to the current design** (Tailwind
    classes). The caller must assert that this set is non-empty, so the check
    can never be silently skipped when the palette changes.
    """
    return [b for b in buttons if any(has_class(b, marker) for marker in ACTIVE_CLASS_MARKERS)]


def assert_named_region(root: Node, region_id: str) -> Node:
    """A scroll region: focusable, role=region, named and described."""
    region = find_by_id(root, region_id)
    assert region is not None, f"#{region_id} scroll region is missing"

    assert region.attrs.get("tabindex") == "0", (
        f"#{region_id} must be focusable (tabindex=\"0\") so keyboard users can scroll it"
    )
    assert region.attrs.get("role") == "region", (
        f"#{region_id} must expose role=\"region\""
    )

    name = accessible_name(region, root)
    assert name, (
        f"#{region_id} must have an accessible name (aria-label or aria-labelledby -> existing element)"
    )
    assert has_letter(name), f"#{region_id} accessible name must be human-readable, got {name!r}"

    described_by = region.attrs.get("aria-describedby", "").strip()
    assert described_by, (
        f"#{region_id} must reference a scroll hint with aria-describedby"
    )
    hint = find_by_id(root, described_by.split()[0])
    assert hint is not None, (
        f"#{region_id} aria-describedby=\"{described_by}\" points at a missing element"
    )
    hint_text = node_text(hint).strip()
    assert hint_text, (
        f"#{region_id} aria-describedby=\"{described_by}\" must point at real, non-empty hint text"
    )
    return region


# --------------------------------------------------------------------------- #
# 1. Search input
# --------------------------------------------------------------------------- #
def test_search_input_has_accessible_name() -> None:
    """#model-search must be announced: a placeholder is not a label."""
    dom = page()
    search = find_by_id(dom.root, "model-search")
    assert search is not None, "#model-search input is missing"
    assert search.tag == "input", f"#model-search must be an <input>, got <{search.tag}>"

    name = accessible_name(search, dom.root)
    assert name, (
        "#model-search has no accessible name: expected <label for=\"model-search\">, "
        "aria-label, or aria-labelledby pointing at a real element"
    )
    assert has_letter(name), f"#model-search accessible name must be human-readable, got {name!r}"


# --------------------------------------------------------------------------- #
# 2. Selection groups
# --------------------------------------------------------------------------- #
def test_filter_groups_are_named_groups_with_aria_pressed() -> None:
    """role / domain / version buttons expose their state and group name."""
    dom = page()

    groups = (
        ("role", "role-tabs", "data-role"),
        ("domain", "domain-filters", "data-domain"),
        ("version", "version-tabs", "data-version"),
    )

    for kind, group_id, state_attr in groups:
        group = find_by_id(dom.root, group_id)
        assert group is not None, f"#{group_id} group container is missing"

        assert group.attrs.get("role") == "group", (
            f"#{group_id} must use role=\"group\" (a tablist without full keyboard "
            f"support is not acceptable), got role={group.attrs.get('role')!r}"
        )

        name = accessible_name(group, dom.root)
        assert name, (
            f"#{group_id} must have an accessible name (aria-label or aria-labelledby -> existing element)"
        )

        buttons = [n for n in iter_nodes(group) if n.tag == "button"]
        assert buttons, f"#{group_id} must contain buttons"

        missing = [b.attrs.get(state_attr) for b in buttons if "aria-pressed" not in b.attrs]
        assert not missing, (
            f"#{group_id}: every button needs aria-pressed, missing for {missing}"
        )

        pressed = [b for b in buttons if b.attrs.get("aria-pressed") == "true"]
        assert len(pressed) == 1, (
            f"#{group_id}: exactly one button must have aria-pressed=\"true\", found {len(pressed)}"
        )

        expected = initial_selection(dom.script, kind)
        assert pressed[0].attrs.get(state_attr) == expected, (
            f"#{group_id}: aria-pressed=\"true\" must be on the initially selected "
            f"{state_attr}={expected!r}, got {pressed[0].attrs.get(state_attr)!r}"
        )

        for button in buttons:
            if button is not pressed[0]:
                assert button.attrs.get("aria-pressed") == "false", (
                    f"#{group_id}: unselected buttons must have aria-pressed=\"false\", "
                    f"got {button.attrs.get('aria-pressed')!r}"
                )

        # Visual state and announced state must never contradict each other.
        # The markers are style specific (current design); if the palette
        # changes, ACTIVE_CLASS_MARKERS must be updated here *together with*
        # the docstring — the check is never silently skipped.
        active = visually_active(buttons)
        assert active, (
            f"#{group_id}: no button carries an active-state marker "
            f"({', '.join(ACTIVE_CLASS_MARKERS)}) — the current design marks the "
            f"selected button with one of them; if the palette changed, update "
            f"ACTIVE_CLASS_MARKERS in this test together with the docstring"
        )
        assert len(active) == 1, (
            f"#{group_id}: exactly one button must carry the active-state marker, "
            f"found {len(active)}"
        )
        assert pressed[0] is active[0], (
            f"#{group_id}: the aria-pressed=\"true\" button must be the visually "
            f"active one"
        )

    assert not find_all(dom.root, role="tablist"), (
        "role=\"tablist\" is out of scope for this change: the filter groups must stay "
        "role=\"group\" toggle-button groups"
    )

    # A static aria-pressed that is never updated would go stale as soon as the
    # user switches role / domain / dataset version.
    #
    # NOTE: this is a *smoke reference* only — the presence of the token in the
    # script says nothing about whether the state is actually kept in sync.
    # The real sync check is a runtime (browser) assertion.
    assert "aria-pressed" in dom.script or "ariaPressed" in dom.script, (
        "the page script should reference aria-pressed so the pressed state can be "
        "updated when the selection changes (smoke reference only — the actual "
        "state sync is verified in the browser, not here)"
    )


# --------------------------------------------------------------------------- #
# 3. Matrix Inspect control
# --------------------------------------------------------------------------- #
TEMPLATE_BUTTON_RE = re.compile(r"<button\b(?P<attrs>[^>]*)>", re.IGNORECASE)
COMPLETE_BUTTON_RE = re.compile(
    r"<button\b(?P<attrs>[^>]*)>(?P<inner>.*?)</button>", re.IGNORECASE | re.DOTALL
)
CREATE_BUTTON_RE = re.compile(
    r"(?P<var>\w+)\s*=\s*document\.createElement\(\s*['\"]button['\"]\s*\)"
)
MODEL_ID_ASSIGN_RE = re.compile(
    r"(?P<var>\w+)\.(?:dataset\.modelId\s*=|setAttribute\(\s*['\"]data-model-id['\"]\s*,)"
)
BUTTON_LOOKUP_RE = re.compile(r"querySelector(?:All)?\s*\(|closest\s*\(")


def test_matrix_rows_render_inspect_button_carrying_model_id() -> None:
    """The Inspect control must be a real button, not a click-only row."""
    dom = page()
    body = dom.function_body("renderMatrix")
    assert body, "renderMatrix() was not found in the page script"

    openings = list(TEMPLATE_BUTTON_RE.finditer(body))
    complete = list(COMPLETE_BUTTON_RE.finditer(body))
    created = {m.group("var") for m in CREATE_BUTTON_RE.finditer(body)}
    assigned = {m.group("var") for m in MODEL_ID_ASSIGN_RE.finditer(body)}

    # 1. the row must contain a real button
    assert openings or created, (
        "renderMatrix() must render a real <button> for the Inspect control "
        "(a template literal <button ...> or document.createElement('button')); "
        "a click-only <tr onclick> row with a decorative span does not qualify"
    )

    # 2. the model id must be attached somewhere in the row rendering
    assert "data-model-id" in body or assigned, (
        "renderMatrix() must attach the model id to the Inspect control "
        "(data-model-id=\"...\" in the markup, or btn.dataset.modelId = ...)"
    )

    # 3. the model id must end up on the button itself
    bound = any("data-model-id" in m.group("attrs") for m in complete)
    if created & assigned:
        # a button created through the DOM API and stamped with the model id
        bound = True
    if openings and assigned and BUTTON_LOOKUP_RE.search(body):
        # hybrid: the template button is looked up and stamped afterwards
        bound = True
    assert bound, (
        "the model id must be attached to the Inspect <button> itself "
        "(data-model-id on the button, or a button variable that receives the model id)"
    )

    # 4. the button must have an accessible name
    named = False
    for match in complete:
        if re.search(r"aria-label\s*=\s*['\"]", match.group("attrs")):
            named = True
            break
        visible = re.sub(r"\$\{[^}]*\}", " ", re.sub(r"<[^>]+>", " ", match.group("inner")))
        if has_letter(visible.strip()):
            named = True
            break
    if not named:
        for var in sorted(created | assigned):
            if re.search(rf"{re.escape(var)}\.(?:textContent|innerHTML|innerText)\s*=", body):
                named = True
                break
            if re.search(rf"{re.escape(var)}\.setAttribute\(\s*['\"]aria-label['\"]", body):
                named = True
                break
    assert named, (
        "the Inspect <button> must have an accessible name (visible text or aria-label)"
    )

    # The click path to the detail modal may live in renderMatrix() or in a
    # delegated listener, so only the page script as a whole is checked.
    assert "openModal" in dom.script, (
        "the page must keep a path from the Inspect control to the model detail modal (openModal)"
    )


# --------------------------------------------------------------------------- #
# 4. Modal
# --------------------------------------------------------------------------- #
def test_modal_is_a_dialog_labelled_by_a_real_heading() -> None:
    """#modal must be an announced, modal dialog with a real label."""
    dom = page()
    modal = find_by_id(dom.root, "modal")
    assert modal is not None, "#modal is missing"

    assert modal.attrs.get("role") == "dialog", (
        f"#modal must have role=\"dialog\", got {modal.attrs.get('role')!r}"
    )
    assert modal.attrs.get("aria-modal") == "true", (
        "#modal must have aria-modal=\"true\""
    )

    labelled_by = modal.attrs.get("aria-labelledby", "").strip()
    assert labelled_by, (
        "#modal must reference its title with aria-labelledby"
    )

    target_id = labelled_by.split()[0]
    target = find_by_id(dom.root, target_id)
    if target is not None:
        assert target.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}, (
            f"#modal aria-labelledby must point at a real heading, got <{target.tag}>"
        )
        assert node_text(target).strip(), (
            "the heading referenced by #modal aria-labelledby must carry text"
        )
        return

    # The title may be rendered into the dialog by the script instead of being
    # static markup; it must still be a real heading with a non-empty label.
    generated = re.search(
        rf"<(h[1-6])\b[^>]*\bid\s*=\s*['\"]{re.escape(target_id)}['\"][^>]*>(.*?)</\1>",
        dom.script,
        re.S,
    )
    assert generated, (
        f"#modal aria-labelledby=\"{labelled_by}\" points at an element that does not exist "
        "neither in the markup nor in the rendered dialog"
    )
    inner = generated.group(2).strip()
    assert inner, (
        "the heading referenced by #modal aria-labelledby must carry text"
    )


def test_modal_close_button_has_accessible_name() -> None:
    """#modal-close must be announced, not just a glyph."""
    dom = page()
    close = find_by_id(dom.root, "modal-close")
    assert close is not None, "#modal-close is missing"
    assert close.tag == "button", f"#modal-close must be a <button>, got <{close.tag}>"

    name = accessible_name(close, dom.root)
    assert name, "#modal-close has no accessible name"
    assert has_letter(name), (
        f"#modal-close accessible name must be human-readable (not a bare glyph), got {name!r}"
    )


# --------------------------------------------------------------------------- #
# 5. Scrollable regions
# --------------------------------------------------------------------------- #
def test_matrix_table_lives_in_a_named_focusable_scroll_region() -> None:
    """The leaderboard table must be scrollable by keyboard and announced."""
    dom = page()
    region = assert_named_region(dom.root, "matrix-scroll")

    tables = [t for t in find_all(dom.root, "table") if is_descendant(t, region)]
    assert tables, "the matrix <table> must live inside #matrix-scroll"

    matrix_tbody = find_by_id(dom.root, "matrix-tbody")
    assert matrix_tbody is not None, "#matrix-tbody is missing"
    assert any(is_descendant(matrix_tbody, table) for table in tables), (
        "#matrix-tbody must stay inside the #matrix-scroll table"
    )


def test_submissions_table_lives_in_a_named_focusable_scroll_region() -> None:
    """The submissions table must be scrollable by keyboard and announced."""
    dom = page()
    region = assert_named_region(dom.root, "submissions-scroll")

    # The renderer target is the stable id #submissions-container (the table is
    # written into it). How the script looks it up (getElementById, querySelector,
    # ...) is irrelevant — but the id itself is not optional, otherwise the
    # region could be empty while the check still passes.
    container = find_by_id(dom.root, "submissions-container")
    assert container is not None, (
        "#submissions-container (the stable renderer target of the submissions "
        "table) is missing"
    )
    assert is_descendant(container, region), (
        "#submissions-container must live inside #submissions-scroll"
    )
    assert "submissions-container" in dom.script, (
        "the page script must still render the submissions table into "
        "#submissions-container"
    )


def test_both_tables_are_preserved() -> None:
    """Guard rail: the mobile refactor must not drop either table."""
    dom = page()

    tables = find_all(dom.root, "table")
    assert tables, "the static matrix <table> is missing"

    tbody = find_by_id(dom.root, "matrix-tbody")
    assert tbody is not None, "#matrix-tbody is missing"
    assert any(is_descendant(tbody, table) for table in tables), (
        "#matrix-tbody must stay inside a <table>"
    )

    matrix_head = None
    for table in tables:
        if not is_descendant(tbody, table):
            continue
        heads = [n for n in iter_nodes(table) if n.tag == "thead"]
        if heads:
            matrix_head = heads[0]
            break
    assert matrix_head is not None, "the matrix table must keep its <thead>"

    columns = [n for n in iter_nodes(matrix_head) if n.tag == "th"]
    assert len(columns) >= 5, (
        f"the matrix table must keep its columns, found {len(columns)} <th> cells"
    )

    submissions_body = dom.function_body("renderSubmissions")
    assert submissions_body, "renderSubmissions() was not found in the page script"
    assert "<table" in submissions_body, (
        "the submissions table must stay a <table> (not be converted into a card list)"
    )
    submission_columns = len(re.findall(r"<th\b", submissions_body))
    assert submission_columns >= 4, (
        f"the submissions table must keep its columns, found {submission_columns} <th> cells"
    )


# --------------------------------------------------------------------------- #
# 6. Navigation
# --------------------------------------------------------------------------- #
def test_primary_navigation_landmark_and_mobile_toggle() -> None:
    """Navigation must be a named landmark with a working mobile trigger."""
    dom = page()

    navs = find_all(dom.root, "nav")
    assert navs, "the page must expose a <nav> landmark"

    named_navs = [nav for nav in navs if accessible_name(nav, dom.root)]
    assert named_navs, "<nav> must have an accessible name (aria-label / aria-labelledby)"

    primary = find_by_id(dom.root, "primary-navigation")
    assert primary is not None, "#primary-navigation is missing"

    assert any(nav is primary or is_descendant(primary, nav) for nav in named_navs), (
        "#primary-navigation must be the named <nav> landmark (or live inside it)"
    )

    links = [
        a for a in iter_nodes(primary)
        if a.tag == "a" and a.attrs.get("href", "").startswith("#")
    ]
    assert len(links) >= 2, (
        f"#primary-navigation must hold the in-page section links, found {len(links)}"
    )

    toggle = find_by_id(dom.root, "mobile-nav-toggle")
    assert toggle is not None, "#mobile-nav-toggle is missing"
    assert toggle.tag == "button", f"#mobile-nav-toggle must be a <button>, got <{toggle.tag}>"
    assert toggle.attrs.get("aria-expanded") == "false", (
        "#mobile-nav-toggle must start collapsed: aria-expanded=\"false\", got "
        f"{toggle.attrs.get('aria-expanded')!r}"
    )
    assert toggle.attrs.get("aria-controls") == "primary-navigation", (
        "#mobile-nav-toggle must point at #primary-navigation via aria-controls"
    )
    name = accessible_name(toggle, dom.root)
    assert name and has_letter(name), (
        f"#mobile-nav-toggle needs a human-readable accessible name, got {name!r}"
    )


# --------------------------------------------------------------------------- #
# 7. Preserved dataset paths
# --------------------------------------------------------------------------- #
def test_dataset_version_paths_and_switcher_are_preserved() -> None:
    """Both dataset versions must keep their data files and switcher buttons."""
    dom = page()

    paths = {}
    for version in ("1.0.0", "1.1.0"):
        match = re.search(
            rf"['\"]{re.escape(version)}['\"]\s*:\s*\{{[^}}]*?\bfile\s*:\s*['\"]([^'\"]+)['\"]",
            dom.script,
            re.S,
        )
        assert match, f"DATASET_VERSIONS must keep the {version} entry with its data file"
        paths[version] = match.group(1)

    assert paths["1.0.0"] == "data/benchmark_runs-1.0.0.json", (
        f"v1.0.0 must still load data/benchmark_runs-1.0.0.json, got {paths['1.0.0']!r}"
    )
    assert paths["1.1.0"] == "data/benchmark_runs.json", (
        f"v1.1.0 must still load data/benchmark_runs.json, got {paths['1.1.0']!r}"
    )

    for version, relative in paths.items():
        data_file = ROOT / relative
        assert data_file.exists(), f"dataset file for v{version} is missing: {relative}"
        payload = json.loads(data_file.read_text(encoding="utf-8"))
        assert isinstance(payload, list), f"{relative} must stay a JSON list of benchmark tasks"

    switcher_versions = {
        node.attrs.get("data-version")
        for node in iter_nodes(dom.root)
        if node.attrs.get("data-version")
    }
    assert {"1.0.0", "1.1.0"} <= switcher_versions, (
        f"the version switcher must offer both datasets, got {sorted(switcher_versions)}"
    )
