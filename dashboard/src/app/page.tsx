// src/app/page.tsx
import Terminal from '@/components/Terminal';
import StatusCard from '@/components/StatusCard';
import VideoGrid from '@/components/VideoGrid';

export default function Dashboard() {
  const dummyLogs = [
    "LOG_START: Init OpenClaw Engine...",
    "CRON: Checking data/queue.json",
    "PROC: Processing 3 pending tasks",
    "FFMPEG: Encoding video_1204.mp4...",
    "UPLOAD: Syncing to archive..."
  ];

  return (
    <main className="min-h-screen p-4 md:p-10 relative selection:bg-green-500 selection:text-black">
      <div className="crt-overlay" />
      
      {/* Top Navigation / Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-10 gap-4">
        <div>
          <h1 className="text-4xl font-black neon-text tracking-tighter uppercase italic hover:skew-x-2 transition-transform cursor-default">
            OpenClaw <span className="text-white opacity-20">v1.0</span>
          </h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
            <p className="text-[10px] text-cyan-400 font-mono tracking-widest uppercase">
              Termux_Node_Active // Localhost:3000
            </p>
          </div>
        </div>
        
        <div className="text-right font-mono text-[10px] opacity-40 uppercase leading-tight">
          System: Linux aarch64<br/>
          Env: Termux_Mobile<br/>
          Dev: Zyel / Xumu
        </div>
      </div>

      {/* Analytics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        <StatusCard label="In Queue" value="12" colorClass="text-amber-400" />
        <StatusCard label="Processed" value="1.2k" colorClass="text-green-400" />
        <StatusCard label="Failed" value="0" colorClass="text-red-500" />
        <StatusCard label="Uptime" value="142h" colorClass="text-cyan-400" />
      </div>

      {/* Main Command Center */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
        {/* Left: Terminal Log */}
        <div className="xl:col-span-7">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-xs font-bold tracking-widest text-green-800 uppercase">Live_Pipeline_Logs</h2>
            <span className="text-[9px] text-green-900">AUTO_REFRESH: ON</span>
          </div>
          <Terminal logs={dummyLogs} />
        </div>
        
        {/* Right: Video Output List */}
        <div className="xl:col-span-5">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-xs font-bold tracking-widest text-green-800 uppercase">Recent_Outputs</h2>
            <span className="text-[9px] text-green-900 underline cursor-pointer hover:text-green-400">VIEW_ALL_ASSETS</span>
          </div>
          <VideoGrid />
        </div>
      </div>

      {/* Footer Decoration */}
      <footer className="mt-20 border-t border-green-900/30 pt-4 flex justify-between items-center opacity-30 text-[9px] font-mono">
        <p>© 2026 OPENCLAW_CORE - NO RIGHTS RESERVED</p>
        <p>[ ACCESS_LEVEL: ROOT ]</p>
      </footer>
    </main>
  );
}

