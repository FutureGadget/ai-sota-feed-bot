from __future__ import annotations

import unittest

from pipeline import render_static_pages as render


# A small two-node graph (one obstacle, one solution) with the cross-edge,
# a related storyline, and evidence — enough to exercise every branch.
OBSTACLE = {
    "slug": "agent-memory",
    "kind": "obstacle",
    "title": "Agents forget across steps and sessions",
    "area": "memory",
    "status": "active",
    "summary": "An agent's working memory is its context window, which resets between runs.",
    "sections": [
        {"heading": "TL;DR", "html": "<p>Memory is a first-class architecture problem.</p>"},
        {"heading": "State of the art", "html": "<p>The field uses <strong>tiered memory</strong>.</p>"},
        {"heading": "What's new", "html": "<p>Local-first single-file stores.</p>"},
    ],
    "solutions": [
        {"slug": "context-compaction", "title": "Context compaction: curate the working set"},
    ],
    "obstacles": [],
    "related_storylines": [{"slug": "deep-research", "label": "Deep Research"}],
    "evidence": [
        {"sid": "2c8ff757b828dee7", "title": "Beyond Prompting: Context Engineering"},
        {"sid": "aaaaaaaaaaaaaaaa", "title": "Cognitive memory architectures"},
    ],
    "updated": "2026-06-21T02:07:38+00:00",
}

SOLUTION = {
    "slug": "context-compaction",
    "kind": "solution",
    "title": "Context compaction: curate the working set",
    "area": None,
    "status": "active",
    "summary": "Summarize, compress, and curate the working set between turns.",
    "sections": [
        {"heading": "TL;DR", "html": "<p>Keep the working set small.</p>"},
        {"heading": "Trade-offs", "html": "<p>Summaries can drop detail.</p>"},
    ],
    "solutions": [],
    "obstacles": [
        {"slug": "agent-memory", "title": "Agents forget across steps and sessions"},
    ],
    "related_storylines": [],
    "evidence": [],
    "updated": "2026-06-21T02:07:38+00:00",
}

NODES = {OBSTACLE["slug"]: OBSTACLE, SOLUTION["slug"]: SOLUTION}

WIKI = {
    "nodes": NODES,
    "areas": [
        {"area": "memory", "label": "Memory & context", "obstacles": ["agent-memory"]},
    ],
}


class WikiCssTest(unittest.TestCase):
    def test_shared_instrument_token_system(self) -> None:
        css = render.WIKI_PAGE_CSS
        self.assertIn("--bg:#f5f7fa;", css)
        self.assertIn("--accent:#2457d6;", css)
        self.assertIn("--bg:#11151c;", css)  # dark
        self.assertIn('"Avenir Next Condensed"', css)
        self.assertIn("ui-monospace", css)
        # Quality floor + no Oat gray hover fill.
        self.assertIn("outline:3px solid color-mix(in srgb,var(--accent) 50%,transparent)", css)
        self.assertIn("@media (prefers-reduced-motion:reduce)", css)
        self.assertIn('menu a[role="button"]:hover', css)
        self.assertIn("background:transparent", css)

    def test_map_row_resets_oat_article_box(self) -> None:
        # PAGE_CSS styles <article> as a rounded card; the adjacency rows must
        # reset that to a borderless hairline row.
        css = render.WIKI_PAGE_CSS
        self.assertIn(
            ".map-row { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:0;\n"
            "      border:0; border-bottom:1px solid var(--border); border-radius:0; padding:0; background:transparent; }",
            css,
        )


class MapBodyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.body = render.wiki_map_body(WIKI)

    def test_returns_none_without_nodes(self) -> None:
        self.assertIsNone(render.wiki_map_body({"nodes": {}, "areas": []}))

    def test_is_an_adjacency_map_not_a_card_grid(self) -> None:
        # Obstacle -> solution structure, grouped by area, with a jump legend.
        self.assertIn('class="map"', self.body)
        self.assertIn('class="map-legend"', self.body)
        self.assertIn('class="map-area"', self.body)
        self.assertIn('id="area-memory"', self.body)
        self.assertIn('class="map-row"', self.body)
        self.assertIn(">Obstacle<", self.body)
        self.assertIn(">Solved by<", self.body)
        # No generic recap card / pill classes.
        self.assertNotIn('class="articles"', self.body)
        self.assertNotIn('class="toc"', self.body)

    def test_obstacle_links_to_its_solution(self) -> None:
        self.assertIn('href="/topic/agent-memory"', self.body)
        self.assertIn('href="/topic/context-compaction"', self.body)

    def test_solutions_index_lists_every_solution(self) -> None:
        self.assertIn('class="map-solindex"', self.body)
        self.assertIn("Solutions in this map", self.body)

    def test_hero_readout_counts(self) -> None:
        self.assertIn("What breaks when you ship an agent", self.body)
        self.assertIn("1 obstacle", self.body)
        self.assertIn("1 solution", self.body)
        self.assertIn("1 area", self.body)


class TopicBodyTest(unittest.TestCase):
    def test_obstacle_readout_hero(self) -> None:
        hero = render.wiki_topic_hero(OBSTACLE)
        self.assertIn('class="wiki-headline"', hero)
        self.assertIn("<h2", hero)  # topbar already owns the page <h1>
        self.assertIn("🧱 Obstacle", hero)
        self.assertIn("memory", hero)
        self.assertIn("active", hero)
        self.assertIn("2 sources", hero)
        self.assertIn("updated 2026-06-21", hero)

    def test_obstacle_body_is_a_problem_readout(self) -> None:
        body = render.render_topic_body(OBSTACLE, NODES)
        # TL;DR becomes the lead, not a dossier section.
        self.assertIn('class="topic-lead"', body)
        self.assertIn("first-class architecture problem", body)
        # Graph neighborhood panel, high, with the obstacle -> solution edge.
        self.assertIn('class="topic-xlinks"', body)
        self.assertIn("→ Solved by", body)
        self.assertIn('href="/topic/context-compaction"', body)
        self.assertIn("Tracked in storylines", body)
        self.assertIn('href="/storyline/deep-research"', body)
        # Remaining sections render as left-rail dossier entries.
        self.assertIn('class="topic-section"', body)
        self.assertIn("State of the art", body)
        self.assertIn("What&#x27;s new", body)
        # Evidence ledger resolves sids to durable /story permalinks.
        self.assertIn("Evidence · 2 sources", body)
        self.assertIn('href="/story/2c8ff757b828dee7"', body)

    def test_lead_precedes_xlinks_precedes_sections(self) -> None:
        body = render.render_topic_body(OBSTACLE, NODES)
        self.assertLess(body.index("topic-lead"), body.index("topic-xlinks"))
        self.assertLess(body.index("topic-xlinks"), body.index("topic-section"))

    def test_solution_uses_addresses_edge(self) -> None:
        body = render.render_topic_body(SOLUTION, NODES)
        self.assertIn("→ Addresses", body)
        self.assertIn('href="/topic/agent-memory"', body)
        self.assertIn("Trade-offs", body)
        # A solution with no evidence/storylines still renders cleanly.
        self.assertNotIn("Tracked in storylines", body)
        self.assertNotIn("Evidence ·", body)

    def test_unknown_cross_links_are_dropped(self) -> None:
        # An edge to a node not in the graph must not produce a dead link.
        node = dict(OBSTACLE, solutions=[{"slug": "missing-node", "title": "Ghost"}])
        body = render.render_topic_body(node, NODES)
        self.assertNotIn("missing-node", body)
        self.assertNotIn("Ghost", body)


if __name__ == "__main__":
    unittest.main()
