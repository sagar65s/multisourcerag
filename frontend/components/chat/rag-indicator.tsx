"use client";

import { motion, useReducedMotion } from "framer-motion";

const labels = { idle: "Ready", understanding: "Understanding question", searching: "Searching knowledge", verifying: "Verifying evidence", generating: "Generating answer" } as const;
export type RagStage = keyof typeof labels;

export function RagIndicator({ stage }: { stage: RagStage }) {
  const reduce = useReducedMotion();
  if (stage === "idle") return null;
  return <div className="rag-indicator" role="status"><div className="thinking-triangles">{[0, 1, 2].map((i) => <motion.span key={i} animate={reduce ? undefined : { rotate: [0, 120, 240, 360], y: [0, -4, 0] }} transition={{ repeat: Infinity, duration: 1.8, delay: i * .15 }} />)}</div><span>{labels[stage]}</span></div>;
}

