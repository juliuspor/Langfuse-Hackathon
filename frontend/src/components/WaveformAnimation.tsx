import { cn } from "@/lib/utils";

interface WaveformAnimationProps {
  isPlaying: boolean;
  color?: "speaker-1" | "speaker-2";
  barCount?: number;
}

export default function WaveformAnimation({ isPlaying, color = "speaker-1", barCount = 5 }: WaveformAnimationProps) {
  return (
    <div className="flex items-center gap-[3px] h-6">
      {Array.from({ length: barCount }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "w-[3px] rounded-full transition-all duration-200",
            color === "speaker-1" ? "bg-speaker-1" : "bg-speaker-2",
            isPlaying ? "wave-bar" : "h-1 opacity-30"
          )}
          style={{
            animationDelay: `${i * 0.15}s`,
            height: isPlaying ? "100%" : undefined,
          }}
        />
      ))}
    </div>
  );
}
