import { motion, AnimatePresence } from "framer-motion";
import {
  Pause,
  Play,
  ChevronDown,
  ListMusic,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { DEFAULT_TURNS, startLiveDebate } from "@/lib/api";
import {
  SPEAKERS,
  type DebateTurn,
  type NewsHeadline,
  type RefereeVerdict,
} from "@/lib/debateData";
import WaveformAnimation from "./WaveformAnimation";
import { cn } from "@/lib/utils";

interface LivePodcastProps {
  headline: NewsHeadline;
  onBack: () => void;
}

type DebateStatus = "connecting" | "streaming" | "completed" | "error";

const REFEREE_STYLES: Record<
  RefereeVerdict["verdict"],
  { badgeClass: string; noteClass: string }
> = {
  green: {
    badgeClass: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
    noteClass: "text-emerald-100",
  },
  yellow: {
    badgeClass: "border-amber-400/30 bg-amber-500/10 text-amber-100",
    noteClass: "text-amber-50",
  },
  red: {
    badgeClass: "border-rose-400/30 bg-rose-500/10 text-rose-100",
    noteClass: "text-rose-50",
  },
  offside: {
    badgeClass: "border-sky-400/30 bg-sky-500/10 text-sky-100",
    noteClass: "text-sky-50",
  },
};

function getRefereeStyles(verdict?: RefereeVerdict["verdict"]) {
  if (!verdict) {
    return {
      badgeClass: "border-border bg-secondary text-muted-foreground",
      noteClass: "text-foreground",
    };
  }
  return REFEREE_STYLES[verdict];
}

function buildRefereeScore(turns: DebateTurn[]) {
  const score = {
    agent_1: { yellow: 0, offside: 0, red: 0 },
    agent_2: { yellow: 0, offside: 0, red: 0 },
  };

  turns.forEach((turn) => {
    const verdict = turn.referee?.verdict;
    if (!verdict || verdict === "green") {
      return;
    }
    score[turn.speaker][verdict] += 1;
  });

  return `${SPEAKERS.agent_1.shortName} ${score.agent_1.yellow} Gelb, ${score.agent_1.offside} Abseits, ${score.agent_1.red} Rot · ${SPEAKERS.agent_2.shortName} ${score.agent_2.yellow} Gelb, ${score.agent_2.offside} Abseits, ${score.agent_2.red} Rot`;
}

function ElapsedTime({ isRunning }: { isRunning: boolean }) {
  const [sec, setSec] = useState(0);
  useEffect(() => {
    if (!isRunning) return;
    const id = setInterval(() => setSec((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [isRunning]);
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return (
    <span className="text-[10px] text-muted-foreground tabular-nums">
      {m}:{s.toString().padStart(2, "0")}
    </span>
  );
}

export default function LivePodcast({ headline, onBack }: LivePodcastProps) {
  const [turns, setTurns] = useState<DebateTurn[]>([]);
  const [status, setStatus] = useState<DebateStatus>("connecting");
  const [activeSpeaker, setActiveSpeaker] = useState<"agent_1" | "agent_2" | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [currentAudioTurn, setCurrentAudioTurn] = useState<DebateTurn | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [isAudioBlocked, setIsAudioBlocked] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [factRefereeEnabled, setFactRefereeEnabled] = useState(false);
  const [latestRefereeVerdict, setLatestRefereeVerdict] =
    useState<RefereeVerdict | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const cancelRef = useRef<() => void>();
  const audioQueueRef = useRef<DebateTurn[]>([]);
  const currentAudioTurnRef = useRef<DebateTurn | null>(null);
  const playedAudioTurnsRef = useRef<Set<number>>(new Set());
  const isPausedRef = useRef(false);

  const resetAudio = useCallback(() => {
    audioQueueRef.current = [];
    currentAudioTurnRef.current = null;
    playedAudioTurnsRef.current.clear();
    isPausedRef.current = false;
    setCurrentAudioTurn(null);
    setIsPaused(false);
    setIsAudioBlocked(false);

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.removeAttribute("src");
      audioRef.current.load();
    }
  }, []);

  const playQueuedAudio = useCallback(async () => {
    if (
      isPausedRef.current ||
      currentAudioTurnRef.current ||
      audioQueueRef.current.length === 0
    ) {
      return;
    }

    let nextTurn = audioQueueRef.current.shift();
    while (nextTurn && playedAudioTurnsRef.current.has(nextTurn.turn_index)) {
      nextTurn = audioQueueRef.current.shift();
    }

    const audio = audioRef.current;
    if (!nextTurn?.audio_url || !audio) {
      return;
    }

    currentAudioTurnRef.current = nextTurn;
    setCurrentAudioTurn(nextTurn);
    setActiveSpeaker(nextTurn.speaker);
    setIsAudioBlocked(false);

    audio.src = nextTurn.audio_url;
    audio.load();

    try {
      await audio.play();
      isPausedRef.current = false;
      setIsPaused(false);
    } catch {
      isPausedRef.current = true;
      setIsPaused(true);
      setIsAudioBlocked(true);
    }
  }, []);

  const enqueueAudio = useCallback(
    (turn: DebateTurn) => {
      if (!turn.audio_url || playedAudioTurnsRef.current.has(turn.turn_index)) {
        return;
      }
      if (currentAudioTurnRef.current?.turn_index === turn.turn_index) {
        return;
      }
      if (
        audioQueueRef.current.some(
          (queued) => queued.turn_index === turn.turn_index
        )
      ) {
        return;
      }

      audioQueueRef.current.push(turn);
      void playQueuedAudio();
    },
    [playQueuedAudio]
  );

  const handleAudioEnded = useCallback(() => {
    const endedTurn = currentAudioTurnRef.current;
    if (endedTurn) {
      playedAudioTurnsRef.current.add(endedTurn.turn_index);
    }
    currentAudioTurnRef.current = null;
    setCurrentAudioTurn(null);
    if (audioQueueRef.current.length === 0) {
      setActiveSpeaker(null);
    }
    void playQueuedAudio();
  }, [playQueuedAudio]);

  const handlePlayPause = useCallback(async () => {
    const audio = audioRef.current;

    if (!isPaused) {
      isPausedRef.current = true;
      setIsPaused(true);
      audio?.pause();
      return;
    }

    isPausedRef.current = false;
    setIsPaused(false);
    setIsAudioBlocked(false);

    if (currentAudioTurnRef.current && audio?.src) {
      try {
        await audio.play();
      } catch {
        isPausedRef.current = true;
        setIsPaused(true);
        setIsAudioBlocked(true);
      }
      return;
    }

    void playQueuedAudio();
  }, [isPaused, playQueuedAudio]);

  const startDebate = useCallback(() => {
    cancelRef.current?.();
    resetAudio();
    setTurns([]);
    setStatus("connecting");
    setActiveSpeaker(null);
    setConversationId(null);
    setWarnings([]);
    setErrorMessage(null);
    setFactRefereeEnabled(false);
    setLatestRefereeVerdict(null);

    const cancel = startLiveDebate(headline.headline, DEFAULT_TURNS, true, headline, {
      onConnected: () => setStatus("connecting"),
      onConversation: (conversation) => {
        setConversationId(conversation.conversation_id);
        setStatus("streaming");
        setFactRefereeEnabled(Boolean(conversation.fact_referee_enabled));
      },
      onTurn: (turn) => {
        setTurns((prev) => [...prev, turn]);
        setActiveSpeaker(turn.speaker);
        if (turn.audio_url) {
          enqueueAudio(turn);
        }
      },
      onReferee: (verdict) => {
        setLatestRefereeVerdict(verdict);
        setTurns((prev) =>
          prev.map((item) =>
            item.turn_index === verdict.turn_index
              ? { ...item, referee: verdict }
              : item
          )
        );
      },
      onAudio: (turn) => {
        setTurns((prev) => {
          const hasTurn = prev.some(
            (item) => item.turn_index === turn.turn_index
          );
          if (!hasTurn) {
            return [...prev, turn].sort((a, b) => a.turn_index - b.turn_index);
          }
          return prev.map((item) =>
            item.turn_index === turn.turn_index ? { ...item, ...turn } : item
          );
        });
        enqueueAudio(turn);
      },
      onCompleted: (debate) => {
        setStatus("completed");
        setWarnings(debate.meta?.warnings ?? []);
        setFactRefereeEnabled(Boolean(debate.meta?.fact_referee?.enabled));
        if (debate.turns?.length) {
          setTurns(debate.turns);
          const latestVerdict =
            [...debate.turns]
              .reverse()
              .find((turn) => turn.referee)?.referee ?? null;
          setLatestRefereeVerdict(latestVerdict);
          debate.turns.forEach(enqueueAudio);
        }
        if (!currentAudioTurnRef.current && audioQueueRef.current.length === 0) {
          setActiveSpeaker(null);
        }
      },
      onError: (message) => {
        setErrorMessage(message);
        setStatus("error");
        setActiveSpeaker(null);
      },
    });

    cancelRef.current = cancel;
  }, [enqueueAudio, headline, resetAudio]);

  useEffect(() => {
    startDebate();
    return () => cancelRef.current?.();
  }, [startDebate]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [turns]);

  useEffect(() => {
    if (turns.length > 0) {
      setShowTranscript(true);
    }
  }, [turns.length]);

  const s1 = SPEAKERS.agent_1;
  const s2 = SPEAKERS.agent_2;
  const currentSpeaker = activeSpeaker ? SPEAKERS[activeSpeaker] : null;
  const latestTurn = turns[turns.length - 1] ?? null;
  const latestRefereeStyles = getRefereeStyles(latestRefereeVerdict?.verdict);
  const refereeScore = buildRefereeScore(turns);
  const progressWidth = `${Math.min(
    100,
    status === "completed" ? 100 : Math.max(5, (turns.length / DEFAULT_TURNS) * 100)
  )}%`;

  return (
    <div className="flex flex-col min-h-screen max-w-lg mx-auto bg-background">
      <audio
        ref={audioRef}
        preload="auto"
        onEnded={handleAudioEnded}
        onError={handleAudioEnded}
        className="hidden"
      />

      {/* Clean podcast-player top bar */}
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <button
          onClick={onBack}
          className="p-2 -ml-2 text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronDown className="w-6 h-6" />
        </button>
        <div className="text-center">
          <p className="text-[10px] tracking-wider uppercase text-muted-foreground">
            Podcast wird abgespielt
          </p>
          <p className="text-xs font-medium text-foreground">
            {conversationId ? `Debatte ${conversationId.slice(0, 8)}` : "Lanz & Precht"}
          </p>
        </div>
        <div className="min-w-10 text-right text-[10px] font-medium uppercase tracking-[0.18em] text-primary/80">
          {turns.length}/{DEFAULT_TURNS}
        </div>
      </div>

      {/* Album art / cover area */}
      <div className="flex-1 flex flex-col items-center justify-center px-8 py-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="relative w-full max-w-[320px] aspect-square rounded-xl overflow-hidden shadow-2xl"
        >
          {/* Cover background */}
          <div className="absolute inset-0 bg-gradient-to-br from-secondary via-muted to-background" />

          {/* Studio-style layout */}
          <div className="relative z-10 h-full flex flex-col items-center justify-center p-6">
            {/* LIVE badge */}
            {status === "streaming" && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="absolute top-4 right-4 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-live-red/20 border border-live-red/30"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-live-red live-pulse" />
                <span className="text-[10px] font-bold text-live-red tracking-wider">LIVE</span>
              </motion.div>
            )}

            {/* Two speaker avatars */}
            <div className="flex items-center gap-6 mb-6">
              {/* Lanz */}
              <div className="flex flex-col items-center gap-2">
                <div
                  className={cn(
                    "w-20 h-20 rounded-full flex items-center justify-center font-display font-bold text-xl transition-all duration-500 border-2",
                    "bg-speaker-1/15 text-speaker-1 border-speaker-1/30",
                    activeSpeaker === "agent_1" && "border-speaker-1 speaker-1-glow scale-110"
                  )}
                >
                  {s1.initials}
                </div>
                <span className="text-xs font-display font-semibold text-foreground">{s1.shortName}</span>
                {activeSpeaker === "agent_1" && (
                  <WaveformAnimation isPlaying color="speaker-1" barCount={5} />
                )}
              </div>

              {/* VS divider */}
              <div className="flex flex-col items-center gap-1 opacity-40">
                <span className="text-xs font-display font-bold text-muted-foreground">VS</span>
              </div>

              {/* Precht */}
              <div className="flex flex-col items-center gap-2">
                <div
                  className={cn(
                    "w-20 h-20 rounded-full flex items-center justify-center font-display font-bold text-xl transition-all duration-500 border-2",
                    "bg-speaker-2/15 text-speaker-2 border-speaker-2/30",
                    activeSpeaker === "agent_2" && "border-speaker-2 speaker-2-glow scale-110"
                  )}
                >
                  {s2.initials}
                </div>
                <span className="text-xs font-display font-semibold text-foreground">{s2.shortName}</span>
                {activeSpeaker === "agent_2" && (
                  <WaveformAnimation isPlaying color="speaker-2" barCount={5} />
                )}
              </div>
            </div>

            {/* Status text */}
            {status === "connecting" && (
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary typing-dot" />
                  <span className="w-1.5 h-1.5 rounded-full bg-primary typing-dot" />
                  <span className="w-1.5 h-1.5 rounded-full bg-primary typing-dot" />
                </div>
                <span className="text-xs text-muted-foreground">Wird vorbereitet…</span>
              </div>
            )}

            {currentSpeaker && status === "streaming" && (
              <motion.p
                key={activeSpeaker}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-xs text-muted-foreground"
              >
                {currentSpeaker.name} spricht…
              </motion.p>
            )}

            {isAudioBlocked && (
              <p className="mt-2 text-xs text-primary">Audio ist bereit. Tippe Play.</p>
            )}

            {currentAudioTurn && !isAudioBlocked && (
              <p className="mt-2 text-[10px] text-muted-foreground">
                Tonspur {currentAudioTurn.turn_index}
              </p>
            )}

            {status === "completed" && (
              <p className="text-xs text-muted-foreground">Diskussion beendet</p>
            )}

            {status === "completed" && warnings.length > 0 && (
              <p className="mt-2 max-w-[220px] text-center text-[10px] leading-relaxed text-muted-foreground">
                {warnings[0]}
              </p>
            )}
          </div>
        </motion.div>

        {/* Title + subtitle below the cover */}
        <div className="w-full max-w-[320px] mt-6">
          <h2 className="font-display font-bold text-foreground text-lg leading-snug line-clamp-2">
            {headline.headline}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">Lanz & Precht · Live-Diskussion</p>
        </div>

        {/* Time-based progress bar */}
        <div className="w-full max-w-[320px] mt-5">
          <div className="h-1 bg-secondary rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-primary rounded-full"
              animate={{ width: progressWidth }}
              transition={{ duration: 2, ease: "linear" }}
            />
          </div>
          <div className="flex justify-between mt-1.5">
            <ElapsedTime isRunning={status === "streaming" && !isPaused} />
            <span className="text-[10px] text-muted-foreground">
              {status === "completed" ? "Fertig" : "Live"}
            </span>
          </div>
        </div>

        {factRefereeEnabled && (
          <div className="w-full max-w-[320px] mt-4 rounded-xl border border-border bg-card/70 px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-primary/80">
                  Fakten-Schiri
                </p>
                <p
                  className={cn(
                    "mt-2 text-sm leading-relaxed",
                    latestRefereeStyles.noteClass
                  )}
                >
                  {latestRefereeVerdict
                    ? latestRefereeVerdict.reason
                    : "Prueft noch den ersten Schlagabtausch."}
                </p>
              </div>
              <span
                className={cn(
                  "shrink-0 rounded-full border px-2 py-1 text-[10px] font-semibold",
                  latestRefereeStyles.badgeClass
                )}
              >
                {latestRefereeVerdict?.badge || "Wartet"}
              </span>
            </div>

            {latestRefereeVerdict && (
              <div className="mt-2 flex items-center justify-between gap-3 text-[10px] text-muted-foreground">
                <span>
                  {SPEAKERS[latestRefereeVerdict.speaker].shortName} · Turn{" "}
                  {latestRefereeVerdict.turn_index}
                </span>
                <span>{latestRefereeVerdict.confidence}% sicher</span>
              </div>
            )}

            {status === "completed" && (
              <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
                Endstand: {refereeScore}
              </p>
            )}
          </div>
        )}

        {latestTurn && (
          <motion.div
            key={latestTurn.turn_index}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-[320px] mt-4 rounded-xl border border-border bg-card/80 px-4 py-3"
          >
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-primary/80">
              Jetzt zu horen · {SPEAKERS[latestTurn.speaker].shortName}
            </p>
            <p className="mt-2 text-sm leading-relaxed text-card-foreground line-clamp-4">
              {latestTurn.text}
            </p>
          </motion.div>
        )}
      </div>

      {/* Playback controls */}
      <div className="px-8 pb-4">
        <div className="flex items-center justify-center">
          <button
            onClick={handlePlayPause}
            className="w-14 h-14 rounded-full bg-foreground text-background flex items-center justify-center hover:scale-105 active:scale-95 transition-transform"
            aria-label={isPaused ? "Audio abspielen" : "Audio pausieren"}
          >
            {isPaused ? (
              <Play className="w-6 h-6 ml-0.5" fill="currentColor" />
            ) : (
              <Pause className="w-6 h-6" fill="currentColor" />
            )}
          </button>
        </div>

        {/* Bottom row: transcript toggle */}
        <div className="flex items-center justify-center mt-4">
          <button
            onClick={() => setShowTranscript(!showTranscript)}
            className={cn(
              "inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm transition-colors",
              showTranscript
                ? "border-primary/40 bg-primary/10 text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
            aria-expanded={showTranscript}
          >
            <ListMusic className="w-4 h-4" />
            <span>Transkript</span>
          </button>
        </div>
      </div>

      {/* Transcript drawer */}
      <AnimatePresence>
        {showTranscript && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "40vh", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="border-t border-border overflow-hidden"
          >
            <div ref={scrollRef} className="h-full overflow-y-auto px-4 py-3 space-y-3">
              <p className="text-[10px] text-muted-foreground tracking-wider uppercase mb-2">Transkript</p>
              {turns.map((turn) => {
                const speaker = SPEAKERS[turn.speaker];
                const isLeft = turn.speaker === "agent_1";
                return (
                  <motion.div
                    key={turn.turn_index}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn("flex gap-2", isLeft ? "flex-row" : "flex-row-reverse")}
                  >
                    <div
                      className={cn(
                        "w-6 h-6 rounded-full flex items-center justify-center text-[8px] font-bold font-display flex-shrink-0",
                        isLeft
                          ? "bg-speaker-1/20 text-speaker-1"
                          : "bg-speaker-2/20 text-speaker-2"
                      )}
                    >
                      {speaker.initials}
                    </div>
                    <div className={cn("max-w-[85%]")}>
                      <span
                        className={cn(
                          "text-[9px] font-semibold block mb-0.5",
                          isLeft ? "text-speaker-1" : "text-speaker-2 text-right"
                        )}
                      >
                        {speaker.shortName}
                      </span>
                      <div
                        className={cn(
                          "rounded-2xl px-3 py-2 text-xs leading-relaxed",
                          isLeft
                            ? "bg-secondary rounded-tl-sm"
                            : "bg-secondary rounded-tr-sm"
                        )}
                      >
                        {turn.text}
                      </div>
                      {turn.referee && (
                        <div
                          className={cn(
                            "mt-1.5 flex",
                            isLeft ? "justify-start" : "justify-end"
                          )}
                        >
                          <span
                            className={cn(
                              "rounded-full border px-2 py-0.5 text-[9px] font-semibold",
                              getRefereeStyles(turn.referee.verdict).badgeClass
                            )}
                          >
                            {turn.referee.badge}
                          </span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}

              {status === "streaming" && (
                <div className="flex justify-center py-2">
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground typing-dot" />
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground typing-dot" />
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground typing-dot" />
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error state */}
      {status === "error" && (
        <div className="text-center py-4 border-t border-border">
          <p className="text-sm text-destructive mb-2">
            {errorMessage || "Verbindungsfehler"}
          </p>
          <button
            onClick={startDebate}
            className="text-sm text-primary underline underline-offset-4"
          >
            Erneut versuchen
          </button>
        </div>
      )}
    </div>
  );
}
