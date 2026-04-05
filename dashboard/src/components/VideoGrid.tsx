// dashboard/src/components/VideoGrid.tsx
export default function VideoGrid() {
  const dummyVideos = [
    { id: 1, name: "video_20260401.mp4", status: "COMPLETED" },
    { id: 2, name: "video_20260402.mp4", status: "COMPLETED" },
  ];
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 h-64 overflow-y-auto pr-2 custom-scrollbar">
      {dummyVideos.map((vid) => (
        <div key={vid.id} className="terminal-border bg-black/60 p-3 group cursor-pointer relative overflow-hidden">
          <div className="aspect-video bg-green-900/20 flex items-center justify-center text-[10px] text-green-700 italic border border-green-900/30">
            [PREVIEW_NOT_READY]
          </div>
          <div className="mt-2 flex justify-between items-center">
            <span className="text-[10px] truncate w-32">{vid.name}</span>
            <span className="text-[9px] px-1 bg-green-500/20 text-green-400 border border-green-500/50">
              {vid.status}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

