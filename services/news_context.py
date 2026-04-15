from __future__ import annotations


class NewsContextService:
    def build_context(self, topic: str, language: str) -> dict[str, str]:
        topic_clean = topic.strip()
        if language.lower().startswith("de"):
            context = (
                f"Aktueller Anlass: {topic_clean}. "
                "Mehrere Medienberichte deuten auf eine laufende Entwicklung hin, "
                "die politisch und gesellschaftlich umstritten ist. "
                "Belastbare Details sind noch unvollstaendig, daher sollten Aussagen mit Vorsicht getroffen werden."
            )
            headline = f"Mock-Briefing zu {topic_clean}"
        else:
            context = (
                f"Current topic: {topic_clean}. "
                "Recent coverage suggests an ongoing development with political and social relevance. "
                "Verified details are still incomplete, so claims should be phrased with care."
            )
            headline = f"Mock briefing on {topic_clean}"

        return {
            "source": "mock",
            "headline": headline,
            "context": context,
        }
