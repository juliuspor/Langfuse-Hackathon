import { cn } from "@/lib/utils";

interface SpeakerAvatarProps {
  initials: string;
  name: string;
  role: string;
  color: "speaker-1" | "speaker-2";
  isActive: boolean;
  size?: "sm" | "md";
}

export default function SpeakerAvatar({ initials, name, role, color, isActive, size = "md" }: SpeakerAvatarProps) {
  const sizeClasses = size === "md" ? "w-16 h-16 text-lg" : "w-10 h-10 text-xs";

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative">
        <div
          className={cn(
            "rounded-full flex items-center justify-center font-display font-bold transition-all duration-500",
            sizeClasses,
            color === "speaker-1"
              ? "bg-speaker-1/20 text-speaker-1 border-2 border-speaker-1/40"
              : "bg-speaker-2/20 text-speaker-2 border-2 border-speaker-2/40",
            isActive && color === "speaker-1" && "speaker-1-glow border-speaker-1",
            isActive && color === "speaker-2" && "speaker-2-glow border-speaker-2"
          )}
        >
          {initials}
        </div>
        {isActive && (
          <div className="absolute -bottom-0.5 -right-0.5">
            <span className="relative flex h-3 w-3">
              <span className={cn(
                "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
                color === "speaker-1" ? "bg-speaker-1" : "bg-speaker-2"
              )} />
              <span className={cn(
                "relative inline-flex rounded-full h-3 w-3",
                color === "speaker-1" ? "bg-speaker-1" : "bg-speaker-2"
              )} />
            </span>
          </div>
        )}
      </div>
      {size === "md" && (
        <>
          <span className="text-xs font-display font-semibold text-foreground">{name}</span>
          <span className="text-[10px] text-muted-foreground">{role}</span>
        </>
      )}
    </div>
  );
}
