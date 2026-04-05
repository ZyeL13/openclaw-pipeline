const dummyVideos = [
  { id: 1, name: 'video_20260401_hot.mp4',    status: 'COMPLETED', dur: '0:58' },
  { id: 2, name: 'video_20260402_alpha.mp4',  status: 'COMPLETED', dur: '1:02' },
  { id: 3, name: 'video_20260403_gainers.mp4', status: 'RENDERING', dur: '--:--' },
  { id: 4, name: 'video_20260404_new.mp4',    status: 'QUEUED',    dur: '--:--' },
];

const statusColor: Record<string, string> = {
  COMPLETED: 'text-[var(--teal)] border-[var(--teal-dim)] bg-[var(--teal-glow)]',
  RENDERING: 'text-[var(--amber)] border-[var(--amber-dim)] bg-transparent',
  QUEUED:    'text-[var(--text-dim)] border-[var(--text-muted)] bg-transparent',
};

export default function VideoGrid() {
  return (
    <div
      className="grid grid-cols-1 sm:grid-cols-2 gap-3 h-56 sm:h-64 overflow-y-auto pr-1"
      role="list"
      aria-label="Video output queue"
    >
      {dummyVideos.map((vid) => (
        <div
          key={vid.id}
          role="listitem"
          className="terminal-card p-3 cursor-pointer group"
        >
          <div className="aspect-video bg-[var(--teal-glow)] flex items-center justify-center text-[9px] text-[var(--text-muted)] border border-[var(--border)] mb-2 relative overflow-hidden">
            <span className="italic">[PREVIEW_PENDING]</span>
            <span className="absolute bottom-1 right-1 text-[8px] text-[var(--text-dim)]">{vid.dur}</span>
          </div>
          <div className="flex justify-between items-center gap-1">
            <span className="text-[10px] text-[var(--text-dim)] truncate flex-1 group-hover:text-[var(--text-main)] transition-colors">
              {vid.name}
            </span>
            <span className={`text-[8px] px-1.5 py-0.5 border shrink-0 tracking-widest ${statusColor[vid.status]}`}>
              {vid.status}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
