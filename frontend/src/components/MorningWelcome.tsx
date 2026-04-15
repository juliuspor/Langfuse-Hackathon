import { motion } from "framer-motion";
import { Coffee } from "lucide-react";
import { useEffect, useState } from "react";

interface MorningWelcomeProps {
  onContinue: () => void;
}

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 11) return "Guten Morgen";
  if (h < 17) return "Guten Tag";
  return "Guten Abend";
}

function formatTime(): string {
  return new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

export default function MorningWelcome({ onContinue }: MorningWelcomeProps) {
  const [time, setTime] = useState(formatTime());

  useEffect(() => {
    const id = setInterval(() => setTime(formatTime()), 10_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const t = setTimeout(onContinue, 5000);
    return () => clearTimeout(t);
  }, [onContinue]);

  return (
    <motion.div
      className="flex flex-col items-center justify-center min-h-screen px-6 text-center"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.8 }}
      onClick={onContinue}
    >
      <motion.div
        initial={{ scale: 0, rotate: -20 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ type: "spring", stiffness: 200, delay: 0.3 }}
        className="mb-8"
      >
        <div className="w-20 h-20 rounded-full bg-secondary flex items-center justify-center amber-glow">
          <Coffee className="w-10 h-10 text-primary" />
        </div>
      </motion.div>

      <motion.p
        className="text-muted-foreground text-lg font-light tracking-widest mb-2"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
      >
        {time}
      </motion.p>

      <motion.h1
        className="text-4xl md:text-5xl font-display font-bold text-foreground mb-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
      >
        {getGreeting()}
      </motion.h1>

      <motion.p
        className="text-muted-foreground text-base md:text-lg max-w-xs"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.1 }}
      >
        Was beschäftigt die Welt heute?
      </motion.p>

      <motion.p
        className="mt-12 text-xs text-muted-foreground/50 tracking-widest uppercase"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2 }}
      >
        Tippen zum Fortfahren
      </motion.p>
    </motion.div>
  );
}
