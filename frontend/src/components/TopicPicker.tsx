import { motion } from "framer-motion";
import { Search, Mic } from "lucide-react";
import { type NewsHeadline } from "@/lib/debateData";
import { fetchHeadlines } from "@/lib/api";
import { useCallback, useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface TopicPickerProps {
  onSelectTopic: (headline: NewsHeadline) => void;
}

const CATEGORIES = ["Schlagzeilen", "Deutschland", "Welt", "Wirtschaft", "Wissen", "Sport"];

function formatDate(): string {
  return new Date().toLocaleDateString("de-DE", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function TopicPicker({ onSelectTopic }: TopicPickerProps) {
  const [activeCategory, setActiveCategory] = useState("Schlagzeilen");
  const [headlines, setHeadlines] = useState<NewsHeadline[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadHeadlines = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const feed = await fetchHeadlines(activeCategory, 10);
      setHeadlines(feed.headlines);
    } catch (error) {
      setHeadlines([]);
      setErrorMessage(
        error instanceof Error ? error.message : "Nachrichten konnten nicht geladen werden"
      );
    } finally {
      setIsLoading(false);
    }
  }, [activeCategory]);

  useEffect(() => {
    void loadHeadlines();
  }, [loadHeadlines]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-background/95 backdrop-blur-sm">
        {/* Brand row */}
        <div className="flex items-center justify-between px-4 py-3">
          <h1 className="font-display text-xl font-bold text-foreground tracking-tight">
            <span className="text-primary">Lanz</span>
            <span className="text-muted-foreground mx-1">&</span>
            <span className="text-foreground">Precht</span>
            <span className="text-muted-foreground text-xs font-normal ml-2">News</span>
          </h1>
          <p className="text-[11px] text-muted-foreground hidden sm:block">{formatDate()}</p>
        </div>

        {/* Search bar */}
        <div className="px-4 pb-3">
          <div className="flex items-center gap-2 bg-secondary rounded-full px-4 py-2.5">
            <Search className="w-4 h-4 text-muted-foreground flex-shrink-0" />
            <span className="text-sm text-muted-foreground flex-1">Themen, Quellen durchsuchen</span>
            <Mic className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          </div>
        </div>

        {/* Category tabs */}
        <div className="flex overflow-x-auto no-scrollbar px-2">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={cn(
                "flex-shrink-0 px-3 py-2.5 text-sm font-medium border-b-2 transition-colors",
                activeCategory === cat
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {cat}
            </button>
          ))}
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-3 py-4 space-y-3">
        {isLoading && (
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-5 h-5 rounded-full bg-muted animate-pulse" />
              <span className="h-3 w-24 rounded bg-muted animate-pulse" />
            </div>
            <div className="h-4 w-5/6 rounded bg-muted animate-pulse mb-2" />
            <div className="h-3 w-full rounded bg-muted animate-pulse mb-2" />
            <div className="h-3 w-2/3 rounded bg-muted animate-pulse" />
          </div>
        )}

        {!isLoading && errorMessage && (
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="font-display font-semibold text-[15px] text-card-foreground mb-1.5">
              Keine aktuellen Meldungen
            </p>
            <p className="text-[13px] text-muted-foreground leading-relaxed mb-3">
              {errorMessage}
            </p>
            <button
              onClick={() => void loadHeadlines()}
              className="inline-flex items-center px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-[11px] font-semibold text-primary"
            >
              Erneut laden
            </button>
          </div>
        )}

        {!isLoading && !errorMessage && headlines.length === 0 && (
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="font-display font-semibold text-[15px] text-card-foreground mb-1.5">
              Heute noch ruhig
            </p>
            <p className="text-[13px] text-muted-foreground leading-relaxed">
              Für diese Rubrik wurden gerade keine passenden Meldungen gefunden.
            </p>
          </div>
        )}

        {!isLoading && !errorMessage && headlines.map((h, i) => (
          <motion.article
            key={h.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04, duration: 0.3 }}
          >
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              {/* Main story — tappable */}
              <button
                onClick={() => onSelectTopic(h)}
                className="w-full text-left p-4 hover:bg-secondary/40 transition-colors"
              >
                {/* Source + time */}
                <div className="flex items-center gap-2 mb-2.5">
                  <SourceIcon source={h.source} />
                  <span className="text-xs font-medium text-card-foreground">{h.source}</span>
                  <span className="text-[11px] text-muted-foreground">{h.timeAgo}</span>
                </div>

                {/* Headline */}
                <h3 className="font-display font-semibold text-[15px] text-card-foreground leading-snug mb-1.5">
                  {h.headline}
                </h3>

                {/* Teaser */}
                <p className="text-[13px] text-muted-foreground leading-relaxed line-clamp-2">
                  {h.teaser}
                </p>

                {/* CTA */}
                <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20">
                  <span className="text-sm">🎙️</span>
                  <span className="text-[11px] font-semibold text-primary">Diskussion anhören</span>
                </div>
              </button>

              {/* Related stories */}
              {h.relatedStories && h.relatedStories.length > 0 && (
                <div className="border-t border-border bg-secondary/20">
                  {h.relatedStories.map((rs, j) => (
                    <div
                      key={j}
                      className={cn(
                        "flex items-center gap-3 px-4 py-2.5",
                        j < h.relatedStories!.length - 1 && "border-b border-border/50"
                      )}
                    >
                      <SourceIcon source={rs.source} size="sm" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-card-foreground leading-snug line-clamp-1 font-medium">
                          {rs.headline}
                        </p>
                        <span className="text-[10px] text-muted-foreground">
                          {rs.source} · {rs.timeAgo}
                        </span>
                      </div>
                    </div>
                  ))}
                  <button className="w-full text-center py-2 text-[11px] text-primary font-medium hover:bg-secondary/40 transition-colors">
                    Alle Meldungen anzeigen ›
                  </button>
                </div>
              )}
            </div>
          </motion.article>
        ))}
      </div>
    </div>
  );
}

function SourceIcon({ source, size = "md" }: { source: string; size?: "sm" | "md" }) {
  const colors: Record<string, string> = {
    Tagesschau: "bg-blue-600",
    "ZEIT Online": "bg-stone-600",
    "Der Spiegel": "bg-red-600",
    Handelsblatt: "bg-orange-600",
    FAZ: "bg-sky-700",
    "Süddeutsche Zeitung": "bg-emerald-700",
    BILD: "bg-red-500",
    kicker: "bg-green-600",
    NDR: "bg-blue-500",
    Welt: "bg-sky-600",
    "Berliner Morgenpost": "bg-indigo-600",
    Reuters: "bg-orange-500",
  };
  const bg = colors[source] || "bg-muted-foreground";
  const sizeClass = size === "sm" ? "w-4 h-4 text-[7px]" : "w-5 h-5 text-[9px]";

  return (
    <span className={cn("rounded-full flex items-center justify-center font-bold text-white flex-shrink-0", bg, sizeClass)}>
      {source.charAt(0)}
    </span>
  );
}
