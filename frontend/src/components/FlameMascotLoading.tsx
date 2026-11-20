import React, { useState, useEffect } from 'react';

const ANALYSIS_STATUS_STEPS = [
  "Analyzing runbook...",
  "Reading document...",
  "Finding relevant information...",
  "Generating answer..."
];

interface FlameMascotLoadingProps {
  className?: string;
  hasDocument?: boolean;
}

export const FlameMascotLoading: React.FC<FlameMascotLoadingProps> = ({
  className = "",
  hasDocument = false
}) => {
  const [stepIndex, setStepIndex] = useState(0);
  const [isFading, setIsFading] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setIsFading(true);
      setTimeout(() => {
        setStepIndex((prev) => (prev + 1) % ANALYSIS_STATUS_STEPS.length);
        setIsFading(false);
      }, 250);
    }, 2400);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`analysis-loading-container flex items-center space-x-3 mb-6 select-none ${className}`}>
      {/* Animated Flame Mascot Unit */}
      <div className="flame-mascot-unit flame-mascot-wrapper" title="InfraMind AI">
        {/* Layer 1: Stable Base (Face & Eyes remain stable and recognizable) */}
        <img
          src="/flame-mascot.png"
          alt="InfraMind Flame Mascot"
          className="flame-mascot-base-img flame-mascot-base"
        />
        {/* Layer 2: Upper Flame Head Flickering */}
        <img
          src="/flame-mascot.png"
          alt=""
          className="flame-mascot-upper-tips flame-mascot-upper"
          aria-hidden="true"
        />
        {/* Layer 3: Soft Upward Brightness Pulse */}
        <img
          src="/flame-mascot.png"
          alt=""
          className="flame-mascot-upward-pulse flame-mascot-shimmer"
          aria-hidden="true"
        />
      </div>

      {/* Dynamic Status Text */}
      <div className="flex items-center space-x-1.5">
        <span
          className={`status-text text-[14px] text-[#A3A3A3] font-normal transition-opacity duration-250 ease-in-out ${
            isFading ? 'opacity-0' : 'opacity-100'
          }`}
        >
          {ANALYSIS_STATUS_STEPS[stepIndex]}
        </span>
      </div>
    </div>
  );
};
