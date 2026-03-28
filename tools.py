from crewai.tools import tool

# These are stubs. Griffin will connect them to ChromaDB collections.
# Collection names to confirm with Griffin:
# "app_reviews", "reddit_posts", "g2_reviews", "hn_comments", "competitor_metadata", "ui_screenshots"


@tool("Search App Reviews")
def search_app_reviews(query: str) -> str:
    """Search App Store and Play Store reviews for productivity apps. Returns real user reviews with sentiment scores."""
    return f"[RAG not connected yet] No results for: {query}"


@tool("Search Reddit")
def search_reddit(query: str) -> str:
    """Search Reddit posts and comments from r/productivity, r/notion, r/projectmanagement and related subreddits."""
    return f"[RAG not connected yet] No results for: {query}"


@tool("Search G2 Reviews")
def search_g2_reviews(query: str) -> str:
    """Search G2 verified business user reviews for productivity apps."""
    return f"[RAG not connected yet] No results for: {query}"


@tool("Search HN Comments")
def search_hn_comments(query: str) -> str:
    """Search Hacker News discussions about productivity tools."""
    return f"[RAG not connected yet] No results for: {query}"


@tool("Search Competitor Data")
def search_competitor_data(query: str) -> str:
    """Search metadata, pricing, features, and competitive comparisons for productivity apps."""
    return f"[RAG not connected yet] No results for: {query}"


@tool("Search Screenshots")
def search_screenshots(query: str) -> str:
    """Search UI screenshot descriptions and visual comparisons of competitor productivity apps."""
    return f"[RAG not connected yet] No results for: {query}"
