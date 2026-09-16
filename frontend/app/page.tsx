import { ArrowRight, BookOpenCheck, FileSearch, Globe2, Mic2, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { LandingNav } from "@/components/layout/landing-nav";
import { Button } from "@/components/ui/button";

const capabilities = [
  { Icon: FileSearch, title: "Documents", text: "Ask PDFs, scans, images and office files with page-level evidence." },
  { Icon: Globe2, title: "Web research", text: "Combine indexed websites with current, source-linked web results." },
  { Icon: BookOpenCheck, title: "Verified answers", text: "Cross-check sources, expose conflicts and keep citations beside every answer." },
  { Icon: Mic2, title: "Voice", text: "Ask by microphone and click any AI answer to hear it in English, Tamil or Hindi." },
] as const;

export default function LandingPage() {
  return (
    <main className="landing-page simple-landing">
      <LandingNav />
      <section id="workflow" className="hero section-wrap">
        <div className="hero-copy">
          <div className="eyebrow"><ShieldCheck size={15} /> Private multi-source research</div>
          <h1>One place for every source.<br /><span>One clear answer.</span></h1>
          <p>MultiSource AI connects your documents, websites and current web research, then answers with visible evidence.</p>
          <div className="hero-actions">
            <Button asChild size="lg"><Link href="/login">Get started <ArrowRight size={18} /></Link></Button>
            <Button asChild variant="secondary" size="lg"><a href="#capabilities">See features</a></Button>
          </div>
          <div className="trust-row">
            <span><ShieldCheck size={15} /> Private</span>
            <span><BookOpenCheck size={15} /> Cited</span>
            <span><Globe2 size={15} /> Current</span>
          </div>
        </div>
        <div className="simple-source-card">
          <span>MULTISOURCE AI</span>
          <h2>Documents + Websites + Live Web</h2>
          <p>Search → verify → answer → cite</p>
          <div><FileSearch /><span>+</span><Globe2 /><span>→</span><BookOpenCheck /></div>
        </div>
      </section>
      <section id="capabilities" className="section-wrap capabilities-section">
        <div className="section-heading"><span>CORE FEATURES</span><h2>Simple tools. Strong answers.</h2><p>Everything important stays easy to find and quick to use.</p></div>
        <div className="capability-grid">{capabilities.map(({ Icon, title, text }) => <article className="premium-card" key={title}><div className="card-icon"><Icon size={22} /></div><h3>{title}</h3><p>{text}</p></article>)}</div>
      </section>
      <section id="security" className="section-wrap security-panel simple-security">
        <div className="security-content"><span className="eyebrow"><ShieldCheck size={15} /> Secure by design</span><h2>Your sources stay private.</h2><p>Identity is verified server-side and every database and vector query is scoped to its owner.</p></div>
      </section>
      <footer><div className="brand"><span>△</span> MultiSource AI</div><p>Private, cited research.</p><span>© 2026</span></footer>
    </main>
  );
}
