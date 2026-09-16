import { Plus } from "lucide-react";
import { Reveal } from "@/components/animations/reveal";
import { Button } from "@/components/ui/button";

export function EmptyModule({ title, description, action }: { title: string; description: string; action: string }) {
  return <div className="module-page"><Reveal><header className="page-heading"><div><span className="page-kicker">PRIVATE INTELLIGENCE</span><h1>{title}</h1><p>{description}</p></div><Button><Plus size={18} /> {action}</Button></header></Reveal><Reveal delay={.08}><section className="large-empty"><div className="empty-geometry"><span /><span /><span /></div><h2>Nothing here yet</h2><p>Your content will appear here after the first secure action is completed.</p><Button variant="secondary"><Plus size={17} /> {action}</Button></section></Reveal></div>;
}
