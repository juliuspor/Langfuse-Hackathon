from __future__ import annotations


class NewsContextService:
    def build_context(
        self,
        topic: str,
        language: str,
        article_context: dict[str, str] | None = None,
    ) -> dict[str, str]:
        topic_clean = topic.strip()
        if article_context:
            source = article_context.get("source") or "Nachrichtenquelle"
            teaser = article_context.get("teaser") or "Keine Kurzbeschreibung verfuegbar."
            published_at = article_context.get("published_at")
            published_note = f" Veroeffentlicht: {published_at}." if published_at else ""
            url = article_context.get("url")
            url_note = f" Artikel-URL: {url}." if url else ""
            return {
                "source": "news_article",
                "headline": topic_clean,
                "context": (
                    f"Aktuelle Meldung von {source}: {topic_clean}. "
                    f"Kurzbeschreibung: {teaser}.{published_note}{url_note} "
                    "Diskutiere auf Basis dieser Meldung, ohne ungesicherte Details zu erfinden."
                ),
                "article_source": source,
                "article_url": url or "",
                "published_at": published_at or "",
            }

        if language.lower().startswith("de"):
            context = (
                f"Aktueller Anlass: {topic_clean}. "
                "Mehrere Medienberichte deuten auf eine laufende Entwicklung hin, "
                "die politisch und gesellschaftlich umstritten ist. "
                "Belastbare Details sind noch unvollstaendig, daher sollten Aussagen mit Vorsicht getroffen werden."
            )
            headline = f"Debatte zu {topic_clean}"
        else:
            context = (
                f"Current topic: {topic_clean}. "
                "Recent coverage suggests an ongoing development with political and social relevance. "
                "Verified details are still incomplete, so claims should be phrased with care."
            )
            headline = f"Debate on {topic_clean}"

        return {
            "source": "topic",
            "headline": headline,
            "context": context,
        }
