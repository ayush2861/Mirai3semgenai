import React from 'react';

interface PdfIndexingAnimationProps {
  progress?: number;
}

const REFERENCE_LINES = [
  { left: 'Remappable', right: 'r   e   a   r   buttons', rightClass: 'tracking-[0.16em]' },
  { left: 'Easy', right: 'switching across devices' },
  { left: 'Cloud', right: 'streaming - Remote play - Mobile gaming' },
  { left: 'Low', right: '- latency USB-C connection' },
  { left: 'Instant', right: 'Bluetooth pairing' },
  { left: 'Sweat', right: '-resistant finish' },
  { left: 'Full - size', right: 't   h   u   m   b   s   t   i   c   k   s', rightClass: 'tracking-[0.2em]' },
  { left: 'Laser', right: 'nano 1 textured grips' },
  { left: 'Intensively', right: 'researched and lab X tested' },
  { left: 'Ergonom  i  c', right: 'd   e   s   i   g   n', leftClass: 'tracking-[0.12em]', rightClass: 'tracking-[0.2em]' },
  { left: 'Responsive', right: 'concave cap design' },
  { left: 'Anti', right: '- friction thumbstick rings' },
  { left: 'Ultra', right: '- quiet face inputs' }
];

export const PdfIndexingAnimation: React.FC<PdfIndexingAnimationProps> = ({ progress = 15 }) => {
  return (
    <div className="absolute inset-0 w-full h-full bg-[#000000] rounded-lg overflow-hidden select-none pointer-events-none flex flex-col justify-between">
      {/* Scroll area with top/bottom fade mask */}
      <div
        className="relative w-full h-full overflow-hidden"
        style={{
          maskImage: 'linear-gradient(to bottom, transparent 0%, black 14%, black 86%, transparent 100%)',
          WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 14%, black 86%, transparent 100%)'
        }}
      >
        <div className="animate-pdf-scroll flex flex-col will-change-transform">
          {/* Cycle 1 */}
          <div className="flex flex-col space-y-[3px] py-1">
            {REFERENCE_LINES.map((line, idx) => (
              <div
                key={`c1-${idx}`}
                className="flex items-center justify-between w-full px-1.5 text-[6.5px] leading-[9px] text-[#EDEDED] font-sans font-medium whitespace-nowrap"
              >
                <span className={`text-left shrink-0 ${line.leftClass || ''}`}>{line.left}</span>
                <span className={`text-right truncate ml-1 text-white/90 ${line.rightClass || ''}`}>
                  {line.right}
                </span>
              </div>
            ))}
          </div>

          {/* Cycle 2 (for seamless infinite loop) */}
          <div className="flex flex-col space-y-[3px] py-1">
            {REFERENCE_LINES.map((line, idx) => (
              <div
                key={`c2-${idx}`}
                className="flex items-center justify-between w-full px-1.5 text-[6.5px] leading-[9px] text-[#EDEDED] font-sans font-medium whitespace-nowrap"
              >
                <span className={`text-left shrink-0 ${line.leftClass || ''}`}>{line.left}</span>
                <span className={`text-right truncate ml-1 text-white/90 ${line.rightClass || ''}`}>
                  {line.right}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Subtle bottom progress line */}
      <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#111111] overflow-hidden z-10">
        <div
          className="h-full bg-gradient-to-r from-blue-500 via-sky-400 to-indigo-400 transition-all duration-300 ease-out"
          style={{ width: `${Math.min(Math.max(progress, 8), 100)}%` }}
        />
      </div>
    </div>
  );
};
