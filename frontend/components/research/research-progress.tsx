"use client";

import { Check, LoaderCircle, TriangleAlert } from "lucide-react";

import type { ResearchStage } from "@/services/research.service";

const stages: {key:ResearchStage;label:string}[]=[{key:"planning",label:"Planning"},{key:"searching",label:"Searching"},{key:"reading_sources",label:"Reading sources"},{key:"cross_checking",label:"Cross-checking"},{key:"synthesizing",label:"Synthesizing"},{key:"verifying",label:"Verifying"},{key:"completed",label:"Completed"}];

export function ResearchProgress({stage}:{stage:ResearchStage}){const activeIndex=stages.findIndex(item=>item.key===stage);return <div className="research-progress" role="status" aria-label={`Research status: ${stage.replaceAll("_"," ")}`}>{stages.map((item,index)=>{const done=stage==="completed"||index<activeIndex;const current=item.key===stage;return <div className={`research-step ${done?"done":""} ${current?"current":""} ${stage==="failed"&&index===Math.max(activeIndex,0)?"failed":""}`} key={item.key}><div className="research-node">{done?<Check size={12}/>:current&&stage!=="failed"?<LoaderCircle className="spin" size={12}/>:stage==="failed"?<TriangleAlert size={12}/>:<span>△</span>}</div><span>{item.label}</span></div>})}</div>}

