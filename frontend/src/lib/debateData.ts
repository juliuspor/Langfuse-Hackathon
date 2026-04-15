export interface NewsHeadline {
  id: string;
  headline: string;
  teaser: string;
  source: string;
  source_url?: string | null;
  url?: string | null;
  image_url?: string | null;
  published_at?: string | null;
  timeAgo: string;
  category: string;
  relatedStories?: { headline: string; source: string; timeAgo: string }[];
}

export interface DebateTurn {
  turn_index: number;
  speaker: "agent_1" | "agent_2";
  text: string;
  audio_url?: string;
}

export const SPEAKERS = {
  agent_1: {
    name: "Markus Lanz",
    shortName: "Lanz",
    initials: "ML",
    color: "speaker-1" as const,
    role: "Moderator & Journalist",
  },
  agent_2: {
    name: "Richard David Precht",
    shortName: "Precht",
    initials: "RP",
    color: "speaker-2" as const,
    role: "Philosoph & Autor",
  },
};
