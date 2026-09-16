import { apiFetch } from "@/services/api";
import type { Citation } from "@/components/citations/citation-drawer";

export type ResearchStage = "planning"|"searching"|"reading_sources"|"cross_checking"|"synthesizing"|"verifying"|"completed"|"failed";
export type ResearchSession = { id:string; kind:"deep_research"; title:string; status:ResearchStage; queries:string[]; source_count:number; sources:Citation[]; conflicts:{source_a:string;source_b:string;reason:string}[]; output_markdown:string|null; error_message:string|null; created_at:string; updated_at:string };
export type ResearchInput = { question:string; workspace_id:string|null; include_private:boolean; include_web:boolean; max_queries:number; language:"English"|"Tamil"|"Hindi" };

export const startResearch=(payload:ResearchInput)=>apiFetch<ResearchSession>("/research",{method:"POST",body:JSON.stringify(payload)});
export const getResearch=(id:string)=>apiFetch<ResearchSession>(`/research/${id}`);
export const listResearch=(kind?:ResearchSession["kind"])=>apiFetch<ResearchSession[]>(`/research${kind?`?kind=${kind}`:""}`);
export const deleteResearch=(id:string)=>apiFetch<void>(`/research/${id}`,{method:"DELETE"});
