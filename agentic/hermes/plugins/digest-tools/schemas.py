"""Tool schemas for the digest-tools Hermes plugin."""

VERIFY_URL = {
    "name": "verify_url",
    "description": (
        "Check whether a URL is live: HTTP 2xx/3xx and not a soft-404 page. "
        "Use on every source URL before citing it in research output."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "HTTP(S) URL to verify",
            },
            "timeout": {
                "type": "integer",
                "description": "Request timeout in seconds (default 8)",
            },
        },
        "required": ["url"],
    },
}

FETCH_RSS = {
    "name": "fetch_rss",
    "description": (
        "Fetch one or more RSS/Atom feeds and return article titles, URLs, and "
        "optional bullet stubs. Omit feeds when topic is set to use registry defaults."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Standing topic id — uses registry feeds when feeds omitted",
            },
            "feeds": {
                "type": "array",
                "description": "Feed specs: {label, url, limit?}",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "url": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["url"],
                },
            },
        },
    },
}

READ_PREFLIGHT_CATEGORY = {
    "name": "read_preflight_category",
    "description": (
        "Read raw story stubs from a preflight skeleton category. Lazy-fetches "
        "preflight on cache miss (no central warm step at GO)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "category_id": {
                "type": "string",
                "description": "Preflight category id (e.g. aisearch, robotics)",
            },
            "topic": {
                "type": "string",
                "description": "Topic id for eval fixture routing (defaults to category_id)",
            },
            "prefix": {
                "type": "string",
                "description": "Run prefix for cache paths (from kanban comment or task body)",
            },
            "max_bullets": {
                "type": "integer",
                "description": "Cap on bullets returned (default 12)",
            },
        },
        "required": ["category_id"],
    },
}

READ_CRAWL_MARKDOWN = {
    "name": "read_crawl_markdown",
    "description": (
        "Read Crawl4AI markdown from .cache/<prefix>/crawl/<slug>. Lazy-crawls or "
        "seeds from fixtures on cache miss."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "slug": {
                "type": "string",
                "description": "Cache filename (e.g. artificialanalysis.ai_leaderboards_models.md)",
            },
            "topic": {
                "type": "string",
                "description": "Topic id for eval fixture routing",
            },
            "prefix": {"type": "string", "description": "Run prefix"},
            "max_chars": {
                "type": "integer",
                "description": "Max markdown chars returned (default 8000)",
            },
        },
        "required": ["slug"],
    },
}

READ_STRUCTURED_JSON = {
    "name": "read_structured_json",
    "description": (
        "Read structured leaderboard JSON from .cache/<prefix>/structured/<slug>. "
        "Lazy-fetches on cache miss."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "slug": {
                "type": "string",
                "description": "Cache filename (e.g. swebench_leaderboards.json)",
            },
            "topic": {"type": "string", "description": "Topic id for eval fixture routing"},
            "prefix": {"type": "string", "description": "Run prefix"},
        },
        "required": ["slug"],
    },
}

READ_TOPIC_CONFIG = {
    "name": "read_topic_config",
    "description": (
        "Return the topic registry binding: source kinds, feeds, crawl/structured "
        "slugs, and rubric hints for this research task."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Standing topic id"},
        },
        "required": ["topic"],
    },
}

WEB_SEARCH = {
    "name": "web_search",
    "description": (
        "Search the web for a query. Returns candidate URLs — verify each with "
        "verify_url before citing in output.md."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {
                "type": "integer",
                "description": "Max results (default 5, max 10)",
            },
        },
        "required": ["query"],
    },
}

DIGEST_BOARD_STATUS = {
    "name": "digest_board_status",
    "description": (
        "Return AI Digest kanban pipeline status: per-task kanban state plus "
        "deterministic artifact gate results (output.md, librarian.md, digest.json). "
        "Use for STATUS intent — does not verify ground truth or live URLs."
    ),
    "parameters": {"type": "object", "properties": {}},
}

DIGEST_SETUP_BOARD = {
    "name": "digest_setup_board",
    "description": (
        "Create the AI Digest kanban graph: research × N → librarian → synthesizer. "
        "Assigns orio_researcher, orio_librarian, orio_synthesizer."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "fresh": {
                "type": "boolean",
                "description": "Archive existing digest board tasks first (default false)",
            },
        },
    },
}

DIGEST_GO = {
    "name": "digest_go",
    "description": (
        "Run the full AI Digest agent pipeline: dispatch workers, artifact gates, "
        "render HTML+JSON report. Takes several minutes. Optional fresh board first."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "fresh": {
                "type": "boolean",
                "description": "Archive board and recreate before run (default true)",
            },
            "prefix": {
                "type": "string",
                "description": "Run prefix YYYYMMDDHHMMSS (omit for auto UTC timestamp)",
            },
            "rounds": {
                "type": "integer",
                "description": "Max research dispatch rounds (default 2)",
            },
        },
    },
}

SYNTHESIZE_DIGEST = {
    "name": "synthesize_digest",
    "description": (
        "Compose digest.json from librarian.md in the workspace using the LLM "
        "editorial synthesizer (Instructor structured output). Requires librarian.md "
        "and run prefix. Writes digest.json to the workspace."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "workspace": {
                "type": "string",
                "description": "Absolute path to the kanban task workspace",
            },
            "prefix": {
                "type": "string",
                "description": "Run prefix (from kanban comment or task body)",
            },
        },
        "required": ["workspace", "prefix"],
    },
}
