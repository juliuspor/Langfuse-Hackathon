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

export const MOCK_DEBATE_TURNS: Record<string, DebateTurn[]> = {
  "1": [
    { turn_index: 1, speaker: "agent_1", text: "Guten Morgen! Heute sprechen wir über ein Thema, das die Deutschen wirklich emotional bewegt: das Tempolimit. Richard, Sie sind ja bekennender Befürworter. Warum eigentlich?" },
    { turn_index: 2, speaker: "agent_2", text: "Wissen Sie, Markus, das ist für mich eine Frage der Vernunft. Wir sind das letzte Land in Europa ohne generelles Tempolimit. Das ist doch absurd! Es geht um Sicherheit, um Klimaschutz, um ein Stück Zivilisation." },
    { turn_index: 3, speaker: "agent_1", text: "Aber die Zahlen zeigen doch, dass Autobahnen die sichersten Straßen sind. Die meisten Unfälle passieren innerorts. Ist das nicht ein Scheinargument?" },
    { turn_index: 4, speaker: "agent_2", text: "Da machen Sie es sich zu einfach! Die Schwere der Unfälle auf Autobahnen ist deutlich höher. Und mal ehrlich: Wenn wir als Gesellschaft nicht einmal bereit sind, etwas langsamer zu fahren — wie wollen wir dann die wirklich großen Probleme lösen?" },
    { turn_index: 5, speaker: "agent_1", text: "Das ist jetzt aber sehr philosophisch. Die Autoindustrie sagt, das wäre ein Angriff auf den Wirtschaftsstandort Deutschland. BMW, Mercedes, Porsche — die leben vom Versprechen der Geschwindigkeit." },
    { turn_index: 6, speaker: "agent_2", text: "Und genau das ist das Problem! Wir definieren Freiheit über PS-Zahlen. Das ist ein völlig veraltetes Freiheitsverständnis. Echte Freiheit wäre, in einer lebenswerten Welt alt zu werden." },
    { turn_index: 7, speaker: "agent_1", text: "Da werden Ihnen viele widersprechen. Aber ich muss zugeben: Die Argumente für ein Tempolimit werden stärker. Besonders wenn man sich die CO2-Einsparungen anschaut." },
    { turn_index: 8, speaker: "agent_2", text: "Sehen Sie! Und es kostet nichts. Keine neue Technologie, keine Investitionen. Einfach ein Schild aufstellen. Das ist die effizienteste Klimamaßnahme, die man sich vorstellen kann." },
  ],
};

export function getMockTurnsForTopic(topicId: string): DebateTurn[] {
  return MOCK_DEBATE_TURNS[topicId] || MOCK_DEBATE_TURNS["1"];
}
