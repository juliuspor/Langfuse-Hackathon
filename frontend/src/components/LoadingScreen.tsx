import { motion } from "framer-motion";

interface LoadingScreenProps {
  topic: string;
}

export default function LoadingScreen({ topic }: LoadingScreenProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-6 text-center bg-background">
      {/* Animated rings */}
      <div className="relative w-28 h-28 mb-8">
        <motion.div
          className="absolute inset-0 rounded-full border-2 border-primary/30"
          animate={{ scale: [1, 1.4, 1], opacity: [0.5, 0, 0.5] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute inset-2 rounded-full border-2 border-primary/20"
          animate={{ scale: [1, 1.3, 1], opacity: [0.4, 0, 0.4] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut", delay: 0.3 }}
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center">
            <motion.div
              className="flex items-end gap-[3px] h-8"
              initial={false}
            >
              {[0, 1, 2, 3, 4].map((i) => (
                <motion.div
                  key={i}
                  className="w-[3px] rounded-full bg-primary"
                  animate={{
                    height: ["8px", "24px", "8px"],
                  }}
                  transition={{
                    duration: 0.8,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: i * 0.12,
                  }}
                />
              ))}
            </motion.div>
          </div>
        </div>
      </div>

      {/* Text */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="max-w-[320px]"
      >
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary/80 mb-3">
          Live-Briefing startet
        </p>
        <h2 className="font-display text-2xl font-bold text-foreground mb-3">
          Diskussion wird vorbereitet
        </h2>
        <p className="text-base text-secondary-foreground leading-relaxed mb-2">
          {topic}
        </p>
        <p className="text-sm text-muted-foreground leading-relaxed mb-6">
          Lanz bekommt die erste These, Precht den ersten Widerspruch.
        </p>
      </motion.div>

      {/* Animated steps */}
      <div className="space-y-3 w-full max-w-[260px]">
        <LoadingStep label="Thema wird eingeordnet" delay={0} />
        <LoadingStep label="Erste Reibung entsteht" delay={1.5} />
        <LoadingStep label="Audio und Transcript kommen gleich" delay={3} />
      </div>

      {/* Brand footer */}
      <motion.p
        className="absolute bottom-8 text-[10px] tracking-[0.25em] uppercase text-muted-foreground/40"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
      >
        Lanz & Precht · Live
      </motion.p>
    </div>
  );
}

function LoadingStep({ label, delay }: { label: string; delay: number }) {
  return (
    <motion.div
      className="flex items-center gap-3"
      initial={{ opacity: 0.45 }}
      animate={{ opacity: [0.45, 1, 0.45] }}
      transition={{ duration: 2, repeat: Infinity, delay }}
    >
      <motion.div
        className="w-5 h-5 rounded-full border-2 border-primary/40 flex items-center justify-center"
        animate={{ borderColor: ["hsl(var(--primary) / 0.2)", "hsl(var(--primary) / 0.8)", "hsl(var(--primary) / 0.2)"] }}
        transition={{ duration: 2, repeat: Infinity, delay }}
      >
        <motion.div
          className="w-2 h-2 rounded-full bg-primary"
          animate={{ scale: [0.5, 1, 0.5], opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 2, repeat: Infinity, delay }}
        />
      </motion.div>
      <span className="text-sm text-secondary-foreground">{label}</span>
    </motion.div>
  );
}
