import { useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import MorningWelcome from "@/components/MorningWelcome";
import TopicPicker from "@/components/TopicPicker";
import LoadingScreen from "@/components/LoadingScreen";
import LivePodcast from "@/components/LivePodcast";
import type { NewsHeadline } from "@/lib/mockData";

type Screen = "welcome" | "topics" | "loading" | "podcast";

const Index = () => {
  const [screen, setScreen] = useState<Screen>("topics");
  const [selectedHeadline, setSelectedHeadline] = useState<NewsHeadline | null>(null);

  const handleSelectTopic = useCallback((headline: NewsHeadline) => {
    setSelectedHeadline(headline);
    setScreen("loading");

    // Keep a short broadcast-style handoff before the live stream opens.
    setTimeout(() => {
      setScreen("podcast");
    }, 800);
  }, []);

  const handleBack = useCallback(() => {
    setScreen("topics");
    setSelectedHeadline(null);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AnimatePresence mode="wait">
        {screen === "welcome" && (
          <motion.div key="welcome" exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.3 }}>
            <MorningWelcome onContinue={() => setScreen("topics")} />
          </motion.div>
        )}
        {screen === "topics" && (
          <motion.div
            key="topics"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <TopicPicker onSelectTopic={handleSelectTopic} />
          </motion.div>
        )}
        {screen === "loading" && selectedHeadline && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            <LoadingScreen topic={selectedHeadline.headline} />
          </motion.div>
        )}
        {screen === "podcast" && selectedHeadline && (
          <motion.div
            key="podcast"
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -30 }}
            transition={{ duration: 0.3 }}
          >
            <LivePodcast headline={selectedHeadline} onBack={handleBack} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Index;
