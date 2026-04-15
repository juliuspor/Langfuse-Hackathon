export interface NewsHeadline {
  id: string;
  headline: string;
  teaser: string;
  source: string;
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

export const MOCK_HEADLINES: NewsHeadline[] = [
  {
    id: "1",
    headline: "Bundesregierung beschließt Tempolimit auf Autobahnen ab 2027",
    teaser: "Nach jahrelanger Debatte hat das Kabinett einen Gesetzentwurf für eine generelle Geschwindigkeitsbegrenzung von 130 km/h auf Autobahnen verabschiedet.",
    source: "Tagesschau",
    timeAgo: "vor 2 Std.",
    category: "Schlagzeilen",
    relatedStories: [
      { headline: "ADAC warnt vor Einschränkung der Mobilität", source: "BILD", timeAgo: "vor 3 Std." },
      { headline: "Umweltverbände begrüßen Entscheidung als überfällig", source: "Süddeutsche Zeitung", timeAgo: "vor 1 Std." },
    ],
  },
  {
    id: "2",
    headline: "EU-Kommission legt Regulierung für KI-Arbeitsplätze vor",
    teaser: "Neue Richtlinien sollen den Einsatz von künstlicher Intelligenz in Behörden und Verwaltung regeln. Gewerkschaften fordern Nachbesserungen.",
    source: "ZEIT Online",
    timeAgo: "vor 4 Std.",
    category: "Schlagzeilen",
    relatedStories: [
      { headline: "Welche Jobs sind betroffen? Eine Analyse", source: "FAZ", timeAgo: "vor 5 Std." },
      { headline: "Microsoft kündigt Partnerschaft mit Bundesagentur für Arbeit an", source: "Handelsblatt", timeAgo: "vor 3 Std." },
    ],
  },
  {
    id: "3",
    headline: "Klimaproteste in Berlin: Aktivisten blockieren Regierungsviertel",
    teaser: "Tausende Demonstranten fordern sofortige Maßnahmen gegen den Klimawandel. Der Verkehr in der Innenstadt stand stundenlang still.",
    source: "Der Spiegel",
    timeAgo: "vor 1 Std.",
    category: "Deutschland",
    relatedStories: [
      { headline: "Polizei räumt Blockaden am Brandenburger Tor", source: "Berliner Morgenpost", timeAgo: "vor 45 Min." },
    ],
  },
  {
    id: "4",
    headline: "Mieten in deutschen Großstädten steigen auf neues Rekordhoch",
    teaser: "Laut einer Studie des IW Köln sind die Angebotsmieten im ersten Quartal erneut um 8 Prozent gestiegen.",
    source: "Handelsblatt",
    timeAgo: "vor 6 Std.",
    category: "Wirtschaft",
    relatedStories: [
      { headline: "Hamburg plant Mietpreisbremse für weitere fünf Jahre", source: "NDR", timeAgo: "vor 4 Std." },
      { headline: "Immobilienbranche kritisiert staatliche Eingriffe", source: "Welt", timeAgo: "vor 5 Std." },
    ],
  },
  {
    id: "5",
    headline: "PISA-Studie: Deutsche Schüler fallen weiter zurück",
    teaser: "Die neuesten Ergebnisse zeigen einen anhaltenden Rückgang in Mathematik und Lesekompetenz. Bildungsminister kündigen Sofortprogramm an.",
    source: "FAZ",
    timeAgo: "vor 8 Std.",
    category: "Wissen",
  },
  {
    id: "6",
    headline: "Deutsche Bahn: Neue Schnellstrecke Berlin-Hamburg eröffnet",
    teaser: "Die Fahrzeit zwischen den beiden Städten verkürzt sich auf unter 90 Minuten. Es ist das größte Infrastrukturprojekt des Jahrzehnts.",
    source: "Süddeutsche Zeitung",
    timeAgo: "vor 3 Std.",
    category: "Deutschland",
  },
  {
    id: "7",
    headline: "Scholz und Macron uneins über europäische Verteidigungspolitik",
    teaser: "Beim Gipfeltreffen in Paris zeigten sich deutliche Differenzen über die Finanzierung einer gemeinsamen Armee.",
    source: "Der Spiegel",
    timeAgo: "vor 5 Std.",
    category: "Welt",
    relatedStories: [
      { headline: "NATO fordert höhere Verteidigungsausgaben von Deutschland", source: "Reuters", timeAgo: "vor 7 Std." },
    ],
  },
  {
    id: "8",
    headline: "FC Bayern verliert Champions-League-Halbfinale gegen Real Madrid",
    teaser: "Trotz dominanter erster Halbzeit unterliegt München in der Verlängerung mit 2:3.",
    source: "kicker",
    timeAgo: "vor 10 Std.",
    category: "Sport",
  },
];

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
