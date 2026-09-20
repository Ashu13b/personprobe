import { useState, useEffect, useMemo } from "react";
import type { PersonProfile, SubjectRecordMatrix, PublicRecordRepository, ForensicInquiry } from "../types";
import {
  getForensicsSummary,
  addInvestigationPivot,
  deleteInvestigationPivot,
  addAuxiliaryLead,
  updateAuxiliaryLead,
  deleteAuxiliaryLead,
  runForensicSweep,
  promoteLeadToSource,
  generateForensicInquiries,
  addForensicInquiry,
  updateForensicInquiry,
  deleteForensicInquiry,
  probeForensicInquiry,
  probeAllForensicInquiries,
  getSubjectRecordMatrix,
  expandCivicInquiries,
  registerPublicRepository,
  deletePublicRepository,
  logInquiryFailure,
  profileRef,
} from "../api";
import { safeHref } from "../url";

interface Props {
  profile: PersonProfile;
  onProfileUpdate: (p: PersonProfile) => void;
}

const PIVOT_TYPE_META: Record<string, { label: string; icon: string; bg: string; color: string }> = {
  project_grant: { label: "Project & Grant", icon: "🔬", bg: "#f0fdf4", color: "#166534" },
  institution: { label: "Institution", icon: "🏛️", bg: "#eff6ff", color: "#1e40af" },
  location: { label: "Spatial / Campus", icon: "📍", bg: "#fef3c7", color: "#92400e" },
  associate: { label: "Fellows & Co-Actors", icon: "👥", bg: "#f3e8ff", color: "#6b21a8" },
  gazette_legal: { label: "Gazette & Tribunal", icon: "⚖️", bg: "#fae8ff", color: "#86198f" },
  family_social: { label: "Domestic & Social", icon: "🏡", bg: "#fff1f2", color: "#9f1239" },
  general: { label: "General Anchor", icon: "⚓", bg: "#f1f5f9", color: "#475569" },
};

const INQUIRY_DOMAIN_META: Record<string, { label: string; icon: string; bg: string; color: string }> = {
  academic_degree: { label: "University Degree", icon: "🎓", bg: "#eff6ff", color: "#1d4ed8" },
  doctoral_thesis: { label: "Doctoral Dissertation", icon: "📜", bg: "#f5f3ff", color: "#6d28d9" },
  service_entry: { label: "ARS / Civil Selection", icon: "🏛️", bg: "#fdf4ff", color: "#a21caf" },
  research_grant: { label: "Grant Sanctions", icon: "🔬", bg: "#f0fdf4", color: "#15803d" },
  campus_quarters: { label: "Campus Housing", icon: "📍", bg: "#fefce8", color: "#a16207" },
  superannuation: { label: "Superannuation", icon: "⏱️", bg: "#fff1f2", color: "#be123c" },
  general: { label: "Forensic Deduction", icon: "🧠", bg: "#f8fafc", color: "#334155" },
};

const LEAD_CATEGORY_META: Record<string, { label: string; icon: string; badge: string }> = {
  thesis_dissertation: { label: "Shodhganga Theses", icon: "🎓", badge: "#dbeafe" },
  grant_sanction: { label: "Grant Sanctions & Budget", icon: "💰", badge: "#dcfce7" },
  recruitment_notice: { label: "Fellows & Vacancies", icon: "📋", badge: "#fef3c7" },
  annual_report: { label: "Institute Annual Reports", icon: "📑", badge: "#f1f5f9" },
  electoral_gazette: { label: "Electoral & Housing", icon: "📍", badge: "#fee2e2" },
  legal_tribunal: { label: "CAT & Tribunal Orders", icon: "⚖️", badge: "#f3e8ff" },
  general_lead: { label: "Research Lead", icon: "🔍", badge: "#f8fafc" },
};

export default function ForensicCanvas({ profile, onProfileUpdate }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sweeping, setSweeping] = useState(false);
  const [sweepMsg, setSweepMsg] = useState<string | null>(null);

  // Pivot Modal & Form
  const [showAddPivot, setShowAddPivot] = useState(false);
  const [pivotTitle, setPivotTitle] = useState("");
  const [pivotType, setPivotType] = useState("project_grant");
  const [pivotDesc, setPivotDesc] = useState("");
  const [pivotTime, setPivotTime] = useState("");
  const [pivotLocation, setPivotLocation] = useState("");
  const [pivotEntities, setPivotEntities] = useState("");

  // Lead Modal & Form
  const [showAddLead, setShowAddLead] = useState(false);
  const [leadTitle, setLeadTitle] = useState("");
  const [leadUrl, setLeadUrl] = useState("");
  const [leadCategory, setLeadCategory] = useState("general_lead");
  const [leadPivotId, setLeadPivotId] = useState("");
  const [leadNotes, setLeadNotes] = useState("");
  const [leadQuery, setLeadQuery] = useState("");

  // Filter & Search
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "lead" | "inspected" | "corroborated" | "dead_end">("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Inquiries State & Modal
  const [generatingInquiries, setGeneratingInquiries] = useState(false);
  const [probingInquiryId, setProbingInquiryId] = useState<string | null>(null);
  const [probingAll, setProbingAll] = useState(false);
  const [showAddInquiry, setShowAddInquiry] = useState(false);
  const [inqAnchor, setInqAnchor] = useState("");
  const [inqDomain, setInqDomain] = useState("academic_degree");
  const [inqQuestion, setInqQuestion] = useState("");
  const [inqPaperTrails, setInqPaperTrails] = useState("");
  const [inqQueries, setInqQueries] = useState("");

  // Public Records Atlas State
  const [atlasMatrix, setAtlasMatrix] = useState<SubjectRecordMatrix | null>(null);
  const [loadingAtlas, setLoadingAtlas] = useState(false);
  const [showAtlas, setShowAtlas] = useState(false);
  const [atlasFilter, setAtlasFilter] = useState<"all" | "online" | "offline" | "id_gated">("all");
  const [expandingCivic, setExpandingCivic] = useState(false);

  // Add Custom Repository State
  const [showAddRepo, setShowAddRepo] = useState(false);
  const [savingRepo, setSavingRepo] = useState(false);
  const [repoName, setRepoName] = useState("");
  const [repoDomain, setRepoDomain] = useState("civic_electoral");
  const [repoJurisdiction, setRepoJurisdiction] = useState("state");
  const [repoState, setRepoState] = useState("");
  const [repoDistrict, setRepoDistrict] = useState("");
  const [repoOnlineYear, setRepoOnlineYear] = useState("");
  const [repoOfflineCutoff, setRepoOfflineCutoff] = useState("");
  const [repoDigitizationStatus, setRepoDigitizationStatus] = useState("digitized_open_search");
  const [repoPortalUrl, setRepoPortalUrl] = useState("");
  const [repoSearchTemplate, setRepoSearchTemplate] = useState("");
  const [repoOfflineName, setRepoOfflineName] = useState("");
  const [repoOfflineCustodian, setRepoOfflineCustodian] = useState("");
  const [repoOfflineMethod, setRepoOfflineMethod] = useState("");
  const [repoIdentifiers, setRepoIdentifiers] = useState("");
  const [repoUtilityNotes, setRepoUtilityNotes] = useState("");

  // Failure Learning & Negative Knowledge State
  const [failureModalInquiry, setFailureModalInquiry] = useState<ForensicInquiry | null>(null);
  const [failureMode, setFailureMode] = useState<string>("pre_digitization_cutoff");
  const [failureReason, setFailureReason] = useState("");
  const [failureLesson, setFailureLesson] = useState("");
  const [failureRepoId, setFailureRepoId] = useState("");
  const [loggingFailure, setLoggingFailure] = useState(false);

  const pivots = profile.investigation_pivots ?? [];
  const leads = profile.auxiliary_leads ?? [];
  const inquiries = profile.forensic_inquiries ?? [];

  // Fetch / auto-seed on mount if empty
  useEffect(() => {
    let cancelled = false;
    if (pivots.length === 0 || inquiries.length === 0) {
      setLoading(true);
      getForensicsSummary(profileRef(profile))
        .then(summary => {
          if (!cancelled && summary.ok) {
            onProfileUpdate({
              ...profile,
              investigation_pivots: summary.pivots,
              auxiliary_leads: summary.leads,
              forensic_inquiries: summary.inquiries || profile.forensic_inquiries || [],
            });
          }
        })
        .catch(e => {
          if (!cancelled) setError(String(e));
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }
    return () => {
      cancelled = true;
    };
  }, [profile.name]);

  async function handleGenerateInquiries() {
    setGeneratingInquiries(true);
    setError(null);
    try {
      const resp = await generateForensicInquiries(profileRef(profile));
      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          forensic_inquiries: resp.inquiries,
        });
        setSweepMsg(`Deductive engine formulated ${resp.new_inquiries_count} paper trail hypotheses across university degrees, Ph.D. dissertations, ARS gazettes, and campus records.`);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to generate inquiries");
    } finally {
      setGeneratingInquiries(false);
    }
  }

  async function handleProbeInquiry(inquiryId: string) {
    setProbingInquiryId(inquiryId);
    setError(null);
    try {
      const resp = await probeForensicInquiry(profileRef(profile), inquiryId, "human");
      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          forensic_inquiries: resp.inquiries,
        });
      }
    } catch (err: any) {
      setError(err?.message || "Failed to probe inquiry");
    } finally {
      setProbingInquiryId(null);
    }
  }

  async function handleProbeAllInquiries() {
    setProbingAll(true);
    setError(null);
    try {
      const resp = await probeAllForensicInquiries(profileRef(profile), "human");
      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          forensic_inquiries: resp.inquiries,
        });
        setSweepMsg(`Batch evaluated ${resp.probed_count} inquiries across institutional repositories and archives.`);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to batch probe inquiries");
    } finally {
      setProbingAll(false);
    }
  }

  async function handleExpandCivic() {
    setExpandingCivic(true);
    setError(null);
    try {
      const resp = await expandCivicInquiries(profileRef(profile));
      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          forensic_inquiries: resp.inquiries,
        });
        setSweepMsg(`Added ${resp.added_count} civic, utility (DHBVN), and Gazette of India inquiry anchors.`);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to expand civic inquiries");
    } finally {
      setExpandingCivic(false);
    }
  }

  async function handleToggleAtlas() {
    if (atlasMatrix) {
      setShowAtlas(!showAtlas);
      return;
    }
    setLoadingAtlas(true);
    setError(null);
    try {
      const resp = await getSubjectRecordMatrix(profileRef(profile));
      if (resp.ok) {
        setAtlasMatrix(resp.matrix);
        setShowAtlas(true);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load public records atlas");
    } finally {
      setLoadingAtlas(false);
    }
  }

  async function handleAddRepoSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!repoName.trim()) return;
    setSavingRepo(true);
    try {
      const slug = repoName.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").slice(0, 30);
      const category_id = `${slug}_${Date.now().toString(36)}`;
      const newRepo: Partial<PublicRecordRepository> = {
        category_id,
        category_name: repoName.trim(),
        domain: repoDomain,
        jurisdiction_level: repoJurisdiction,
        state: repoState.trim() || null,
        district_or_city: repoDistrict.trim() || null,
        online_since_year: repoOnlineYear ? parseInt(repoOnlineYear, 10) : null,
        offline_cutoff_year: repoOfflineCutoff ? parseInt(repoOfflineCutoff, 10) : null,
        digitization_status: repoDigitizationStatus,
        portal_url: repoPortalUrl.trim() || null,
        search_query_template: repoSearchTemplate.trim() || null,
        offline_repository_name: repoOfflineName.trim(),
        offline_custodian: repoOfflineCustodian.trim(),
        offline_retrieval_method: repoOfflineMethod.trim(),
        required_identifiers: repoIdentifiers ? repoIdentifiers.split(",").map(s => s.trim()).filter(Boolean) : [],
        forensic_utility_notes: repoUtilityNotes.trim(),
        is_custom: true,
      };

      const resp = await registerPublicRepository(newRepo);
      if (resp.ok) {
        const matResp = await getSubjectRecordMatrix(profileRef(profile));
        if (matResp.ok) {
          setAtlasMatrix(matResp.matrix);
        }
        setRepoName("");
        setRepoState("");
        setRepoDistrict("");
        setRepoOnlineYear("");
        setRepoOfflineCutoff("");
        setRepoPortalUrl("");
        setRepoSearchTemplate("");
        setRepoOfflineName("");
        setRepoOfflineCustodian("");
        setRepoOfflineMethod("");
        setRepoIdentifiers("");
        setRepoUtilityNotes("");
        setShowAddRepo(false);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to register repository");
    } finally {
      setSavingRepo(false);
    }
  }

  async function handleDeleteRepo(categoryId: string, name: string) {
    if (!window.confirm(`Are you sure you want to remove '${name}' from the public records atlas?`)) {
      return;
    }
    try {
      const resp = await deletePublicRepository(categoryId);
      if (resp.ok) {
        const matResp = await getSubjectRecordMatrix(profileRef(profile));
        if (matResp.ok) {
          setAtlasMatrix(matResp.matrix);
        }
      }
    } catch (err: any) {
      setError(err?.message || "Failed to delete repository");
    }
  }

  async function handleLogFailureSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!failureModalInquiry || !failureReason.trim() || !failureLesson.trim()) return;
    setLoggingFailure(true);
    try {
      const resp = await logInquiryFailure(profileRef(profile), failureModalInquiry.inquiry_id, {
        failure_mode: failureMode,
        failure_reason: failureReason.trim(),
        learned_lesson: failureLesson.trim(),
        associated_repository_id: failureRepoId.trim() || undefined,
        actor: "human",
      });

      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          forensic_inquiries: resp.inquiries,
        });

        // If repository was updated with a failure lesson, refresh atlas matrix
        if (failureRepoId.trim()) {
          const matResp = await getSubjectRecordMatrix(profileRef(profile));
          if (matResp.ok) {
            setAtlasMatrix(matResp.matrix);
          }
        }

        setFailureModalInquiry(null);
        setFailureReason("");
        setFailureLesson("");
        setFailureRepoId("");
      }
    } catch (err: any) {
      setError(err?.message || "Failed to log failure learning");
    } finally {
      setLoggingFailure(false);
    }
  }

  async function handleUpdateInquiryStatus(inquiryId: string, status: "open" | "probed" | "confirmed" | "unarchived_offline") {
    try {
      const resp = await updateForensicInquiry(profileRef(profile), inquiryId, { status, actor: "human" });
      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          forensic_inquiries: resp.inquiries,
        });
      }
    } catch (err: any) {
      setError(err?.message || "Failed to update inquiry status");
    }
  }

  async function handleDeleteInquiry(inquiryId: string) {
    if (!confirm("Are you sure you want to remove this deductive inquiry?")) return;
    try {
      const resp = await deleteForensicInquiry(profileRef(profile), inquiryId);
      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          forensic_inquiries: resp.inquiries,
        });
      }
    } catch (err: any) {
      setError(err?.message || "Failed to delete inquiry");
    }
  }

  async function handleAddInquirySubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!inqAnchor.trim() || !inqQuestion.trim()) return;
    try {
      const resp = await addForensicInquiry(profileRef(profile), {
        fact_anchor: inqAnchor.trim(),
        domain: inqDomain,
        deductive_question: inqQuestion.trim(),
        expected_paper_trails: inqPaperTrails.split("\n").map(s => s.trim()).filter(Boolean),
        probe_queries: inqQueries.split("\n").map(s => s.trim()).filter(Boolean),
        actor: "human",
      });
      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          forensic_inquiries: resp.inquiries,
        });
        setShowAddInquiry(false);
        setInqAnchor("");
        setInqDomain("academic_degree");
        setInqQuestion("");
        setInqPaperTrails("");
        setInqQueries("");
      }
    } catch (err: any) {
      setError(err?.message || "Failed to add inquiry");
    }
  }


  async function handleAddPivotSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!pivotTitle.trim()) return;
    try {
      const resp = await addInvestigationPivot(profileRef(profile), {
        title: pivotTitle.trim(),
        pivot_type: pivotType,
        description: pivotDesc.trim(),
        time_period: pivotTime.trim() || undefined,
        location: pivotLocation.trim() || undefined,
        associated_entities: pivotEntities.split(",").map(s => s.trim()).filter(Boolean),
        actor: "human",
      });
      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          investigation_pivots: resp.pivots,
        });
        setShowAddPivot(false);
        setPivotTitle("");
        setPivotDesc("");
        setPivotTime("");
        setPivotLocation("");
        setPivotEntities("");
      }
    } catch (err: any) {
      setError(err?.message || "Failed to add pivot");
    }
  }

  async function handleDeletePivot(pivotId: string) {
    if (!confirm("Are you sure you want to remove this investigation pivot?")) return;
    try {
      const resp = await deleteInvestigationPivot(profileRef(profile), pivotId);
      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          investigation_pivots: resp.pivots,
        });
      }
    } catch (err: any) {
      setError(err?.message || "Failed to delete pivot");
    }
  }

  async function handleAddLeadSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!leadTitle.trim()) return;
    try {
      const resp = await addAuxiliaryLead(profileRef(profile), {
        title: leadTitle.trim(),
        url: leadUrl.trim() || undefined,
        category: leadCategory,
        pivot_id: leadPivotId || undefined,
        lead_notes: leadNotes.trim(),
        automated_query: leadQuery.trim() || undefined,
        actor: "human",
      });
      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          auxiliary_leads: resp.leads,
        });
        setShowAddLead(false);
        setLeadTitle("");
        setLeadUrl("");
        setLeadNotes("");
        setLeadQuery("");
      }
    } catch (err: any) {
      setError(err?.message || "Failed to add auxiliary lead");
    }
  }

  async function handleUpdateLeadStatus(leadId: string, status: "lead" | "inspected" | "corroborated" | "dead_end") {
    try {
      const resp = await updateAuxiliaryLead(profileRef(profile), leadId, { status, actor: "human" });
      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          auxiliary_leads: resp.leads,
        });
      }
    } catch (err: any) {
      setError(err?.message || "Failed to update lead status");
    }
  }

  async function handleDeleteLead(leadId: string) {
    try {
      const resp = await deleteAuxiliaryLead(profileRef(profile), leadId);
      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          auxiliary_leads: resp.leads,
        });
      }
    } catch (err: any) {
      setError(err?.message || "Failed to delete auxiliary lead");
    }
  }

  const [promotingId, setPromotingId] = useState<string | null>(null);

  async function handlePromoteLead(leadId: string) {
    setPromotingId(leadId);
    setError(null);
    try {
      const resp = await promoteLeadToSource(profileRef(profile), leadId, "human");
      if (resp.ok) {
        const updatedLeads = (profile.auxiliary_leads || []).map(l =>
          l.lead_id === leadId ? resp.lead : l
        );
        const updatedSources = resp.already_existed
          ? profile.sources
          : [...profile.sources, resp.promoted_source];

        onProfileUpdate({
          ...profile,
          auxiliary_leads: updatedLeads,
          sources: updatedSources,
        });
        setSweepMsg(
          resp.already_existed
            ? `Source is already in your Wiki Evidence list! Cross-linked with lead.`
            : `Successfully promoted "${resp.lead.title}" to primary Wikipedia Sources with L1 & L2 provenance verified!`
        );
      }
    } catch (err: any) {
      setError(err?.message || "Failed to promote lead to source");
    } finally {
      setPromotingId(null);
    }
  }

  async function handleRunSweep(pivotId?: string) {

    setSweeping(true);
    setSweepMsg(null);
    setError(null);
    try {
      const resp = await runForensicSweep(profileRef(profile), pivotId, "human");
      if (resp.ok) {
        onProfileUpdate({
          ...profile,
          auxiliary_leads: resp.leads,
        });
        setSweepMsg(`Public record sweep generated ${resp.new_leads_count} new investigative leads across Shodhganga, IndianKanoon, ICAR archives, and fellow notices.`);
      }
    } catch (err: any) {
      setError(err?.message || "Sweep failed");
    } finally {
      setSweeping(false);
    }
  }

  const filteredLeads = useMemo(() => {
    return leads.filter(l => {
      if (categoryFilter !== "all" && l.category !== categoryFilter) return false;
      if (statusFilter !== "all" && l.status !== statusFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = l.title.toLowerCase().includes(q);
        const matchNotes = l.lead_notes.toLowerCase().includes(q);
        const matchQuery = (l.automated_query || "").toLowerCase().includes(q);
        if (!matchTitle && !matchNotes && !matchQuery) return false;
      }
      return true;
    });
  }, [leads, categoryFilter, statusFilter, searchQuery]);

  const corroboratedCount = leads.filter(l => l.status === "corroborated").length;

  return (
    <div className="forensic-canvas" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Top Hero Banner */}
      <div
        className="card"
        style={{
          background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)",
          color: "#ffffff",
          padding: "20px 24px",
          border: "none",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 14 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <span style={{ fontSize: 22 }}>🕵️‍♂️</span>
              <h2 style={{ fontSize: 19, fontWeight: 800, margin: 0 }}>
                Forensic Investigation Canvas &amp; Auxiliary Leads
              </h2>
            </div>
            <p style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.5, margin: 0, maxWidth: 780 }}>
              Reconstructing the <strong>institutional, financial, spatial, and human network</strong> footprint behind <strong>{profile.name}</strong>.
              These auxiliary leads (Shodhganga doctoral theses, ICAR grant sanction orders, CPWD housing quarters, fellow recruitment lists) 
              serve as deep investigatory anchors that corroborate identity and never pollute the Wikipedia draft.
            </p>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn-primary"
              onClick={() => handleRunSweep()}
              disabled={sweeping}
              style={{
                fontSize: 12,
                padding: "8px 14px",
                display: "flex",
                alignItems: "center",
                gap: 6,
                background: "#3b82f6",
                border: "none",
              }}
              title="Generate multi-hop OSINT queries across Shodhganga, IndianKanoon, ICAR/DBT tenders, and fellow recruitment rosters"
            >
              {sweeping ? "🔄 Sweeping Public Records…" : "⚡ Run Public Records Sweep"}
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handleGenerateInquiries}
              disabled={generatingInquiries}
              style={{
                fontSize: 12,
                padding: "8px 14px",
                display: "flex",
                alignItems: "center",
                gap: 6,
                background: "#7c3aed",
                border: "none",
              }}
              title="Deduce paper trails from all confirmed educational and professional milestones"
            >
              {generatingInquiries ? "🔄 Formulating Hypotheses…" : "🧠 Deduce Paper Trails"}
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => setShowAddPivot(true)}
              style={{ fontSize: 12, padding: "8px 14px", background: "rgba(255,255,255,0.12)", color: "#fff", borderColor: "rgba(255,255,255,0.2)" }}
            >
              + Add Pivot Anchor
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => setShowAddLead(true)}
              style={{ fontSize: 12, padding: "8px 14px", background: "rgba(255,255,255,0.12)", color: "#fff", borderColor: "rgba(255,255,255,0.2)" }}
            >
              + Log Auxiliary Lead
            </button>
          </div>
        </div>

        {/* Forensic Metrics Bar */}
        <div style={{ display: "flex", gap: 16, marginTop: 16, paddingTop: 14, borderTop: "1px solid rgba(255,255,255,0.12)", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            <span style={{ color: "#93c5fd" }}>🏛️ Anchors / Pivots:</span>
            <strong>{pivots.length}</strong>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            <span style={{ color: "#c4b5fd" }}>🧠 Deductive Inquiries:</span>
            <strong>{inquiries.length}</strong>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            <span style={{ color: "#86efac" }}>📜 Total Auxiliary Leads:</span>
            <strong>{leads.length}</strong>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            <span style={{ color: "#fde047" }}>✓ Corroborated Evidence:</span>
            <strong>{corroboratedCount}</strong>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, marginLeft: "auto" }}>
            <span style={{ color: "#cbd5e1" }}>Pivots Model:</span>
            <span style={{ background: "rgba(255,255,255,0.15)", padding: "1px 6px", borderRadius: 4 }}>Dual-Client (Human &amp; Agent)</span>
          </div>
        </div>
      </div>

      {loading && (
        <div className="card" style={{ padding: "12px 16px", color: "var(--muted)", fontSize: 13 }}>
          🔄 Loading forensic anchors and auxiliary leads…
        </div>
      )}

      {error && (
        <div className="card" style={{ background: "#fee2e2", border: "1px solid #fca5a5", color: "#b91c1c", padding: "10px 14px", fontSize: 13 }}>
          ⚠️ {error}
        </div>
      )}

      {sweepMsg && (
        <div className="card" style={{ background: "#f0fdf4", border: "1px solid #86efac", color: "#166534", padding: "10px 14px", fontSize: 13, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>✓ {sweepMsg}</span>
          <button type="button" onClick={() => setSweepMsg(null)} style={{ background: "none", border: "none", color: "#166534", cursor: "pointer", fontWeight: 700 }}>✕</button>
        </div>
      )}

      {/* Section 1: Investigation Pivots (Entity Anchors) */}
      <div className="card" style={{ padding: "18px 20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: 0 }}>
              Investigation Pivots (Institutional, Project &amp; Spatial Anchors)
            </h3>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: "3px 0 0" }}>
              Anchor points that open up public record searches beyond direct name queries.
            </p>
          </div>
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)" }}>
            {pivots.length} registered anchors
          </span>
        </div>

        {pivots.length === 0 ? (
          <div style={{ padding: "24px", textAlign: "center", color: "var(--muted)", fontSize: 13, border: "1px dashed var(--border)", borderRadius: 8 }}>
            No investigation pivots registered yet. Click &quot;+ Add Pivot Anchor&quot; or run a sweep.
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 12 }}>
            {pivots.map(p => {
              const meta = PIVOT_TYPE_META[p.pivot_type] || PIVOT_TYPE_META.general;
              const relatedLeadsCount = leads.filter(l => l.pivot_id === p.pivot_id).length;

              return (
                <div
                  key={p.pivot_id}
                  style={{
                    padding: "14px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "#ffffff",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    gap: 10,
                  }}
                >
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 6, marginBottom: 6 }}>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: 6,
                          background: meta.bg,
                          color: meta.color,
                          display: "flex",
                          alignItems: "center",
                          gap: 4,
                        }}
                      >
                        <span>{meta.icon}</span>
                        <span>{meta.label}</span>
                      </span>
                      <button
                        type="button"
                        onClick={() => handleDeletePivot(p.pivot_id)}
                        title="Delete this pivot"
                        style={{ background: "none", border: "none", color: "var(--muted)", cursor: "pointer", fontSize: 12 }}
                      >
                        ✕
                      </button>
                    </div>

                    <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 4px", color: "var(--text)" }}>
                      {p.title}
                    </h4>

                    {p.description && (
                      <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 6px", lineHeight: 1.4 }}>
                        {p.description}
                      </p>
                    )}

                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
                      {p.location && (
                        <span style={{ fontSize: 11, background: "#fef3c7", color: "#92400e", padding: "1px 6px", borderRadius: 4 }}>
                          📍 {p.location}
                        </span>
                      )}
                      {p.time_period && (
                        <span style={{ fontSize: 11, background: "#f1f5f9", color: "var(--muted)", padding: "1px 6px", borderRadius: 4 }}>
                          🗓️ {p.time_period}
                        </span>
                      )}
                      {p.associated_entities.map((e, idx) => (
                        <span key={idx} style={{ fontSize: 11, background: "#eff6ff", color: "#1e40af", padding: "1px 6px", borderRadius: 4 }}>
                          {e}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 8, borderTop: "1px solid var(--border)" }}>
                    <span style={{ fontSize: 11, color: "var(--muted)" }}>
                      {relatedLeadsCount} auxiliary lead(s)
                    </span>
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={() => handleRunSweep(p.pivot_id)}
                      disabled={sweeping}
                      style={{ fontSize: 11, padding: "3px 8px" }}
                    >
                      ⚡ Sweep Anchor
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Section 2: Deductive Inquiry Engine ("If This Is True, What Must Exist?") */}
      <div className="card" style={{ padding: "18px 20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 10, marginBottom: 14 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 18 }}>🧠</span>
              <h3 style={{ fontSize: 16, fontWeight: 800, margin: 0 }}>
                Deductive Inquiry Engine: &quot;If This Is True, What Must Exist in Public Records?&quot;
              </h3>
            </div>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: "3px 0 0", maxWidth: 780 }}>
              Deduces the mandatory real-world institutional paper trail (e.g. <em>convocation registers, silver jubilee souvenirs, library thesis deposits, government gazettes, housing rolls</em>) required to substantiate biographical milestones.
            </p>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn-primary"
              onClick={handleGenerateInquiries}
              disabled={generatingInquiries}
              style={{ fontSize: 11, padding: "6px 12px", background: "#7c3aed", border: "none" }}
              title="Deduce paper trails from all confirmed educational and professional milestones"
            >
              {generatingInquiries ? "🔄 Formulating Hypotheses…" : "⚡ Auto-Deduce Hypotheses"}
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handleProbeAllInquiries}
              disabled={probingAll}
              style={{ fontSize: 11, padding: "6px 12px", background: "#059669", border: "none" }}
              title="Batch-probe open inquiries across online archives and match newly discovered sources"
            >
              {probingAll ? "🔍 Probing Archives…" : "🔍 Batch Probe All"}
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={handleExpandCivic}
              disabled={expandingCivic}
              style={{ fontSize: 11, padding: "6px 12px", background: "#fef3c7", color: "#92400e", border: "1px solid #fde68a" }}
              title="Expand inquiries with open-source civic registers: Electoral Rolls, DHBVN Electricity bills, and Gazette of India"
            >
              {expandingCivic ? "🏛️ Expanding…" : "🏛️ Expand Civic Touchpoints"}
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={handleToggleAtlas}
              disabled={loadingAtlas}
              style={{ fontSize: 11, padding: "6px 12px", background: showAtlas ? "#1e40af" : "#f1f5f9", color: showAtlas ? "#ffffff" : "#1e3a8a", border: "1px solid #bfdbfe", fontWeight: 700 }}
              title="Inspect state & national public records directory with digitization cutoffs and statutory custodians"
            >
              {loadingAtlas ? "🗺️ Loading Atlas…" : showAtlas ? "🗺️ Hide Records Atlas" : "🗺️ Public Records Atlas"}
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => setShowAddInquiry(true)}
              style={{ fontSize: 11, padding: "6px 12px" }}
            >
              + Add Custom Hypothesis
            </button>
          </div>
        </div>

        {/* Public Records & Archival Atlas (Digitization Horizons & Reusable Registry) */}
        {showAtlas && atlasMatrix && (
          <div style={{ background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: 8, padding: "14px 16px", marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 10, marginBottom: 12 }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ fontSize: 16 }}>🗺️</span>
                  <h4 style={{ fontSize: 14, fontWeight: 800, margin: 0, color: "#0f172a" }}>
                    Public Records &amp; Archival Atlas (Digitization Horizons &amp; Reusable Registry)
                  </h4>
                  <span style={{ fontSize: 10, background: "#dbeafe", color: "#1e40af", padding: "1px 6px", borderRadius: 4, fontWeight: 700 }}>
                    Jurisdiction: {atlasMatrix.primary_state} {atlasMatrix.primary_districts.length > 0 ? `(${atlasMatrix.primary_districts.join(", ")})` : ""}
                  </span>
                </div>
                <p style={{ fontSize: 11, color: "var(--muted)", margin: "3px 0 0" }}>
                  Pre-mapped across states &amp; institutions: tells you <strong>what is digitized online</strong> vs. <strong>what is locked in pre-cutoff physical stacks</strong> for {profile.name} (born c. {atlasMatrix.birth_year || "Unknown"}).
                </p>
              </div>

              {/* Action Buttons & Filter Pills */}
              <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                <button
                  type="button"
                  onClick={() => setShowAddRepo(true)}
                  style={{ fontSize: 10, padding: "3px 8px", borderRadius: 4, border: "1px solid #93c5fd", background: "#eff6ff", color: "#1d4ed8", fontWeight: 700, cursor: "pointer" }}
                  title="Dynamically register a newly discovered state or institutional public repository"
                >
                  + Register Tested Repository
                </button>
                <div style={{ display: "flex", gap: 4 }}>
                  <button
                    type="button"
                    onClick={() => setAtlasFilter("all")}
                    style={{ fontSize: 10, padding: "3px 8px", borderRadius: 4, border: "1px solid var(--border)", background: atlasFilter === "all" ? "#0f172a" : "#ffffff", color: atlasFilter === "all" ? "#ffffff" : "#475569", fontWeight: 700, cursor: "pointer" }}
                  >
                    All ({atlasMatrix.online_reachable_count + atlasMatrix.id_required_count + atlasMatrix.offline_archives_count})
                  </button>
                  <button
                    type="button"
                    onClick={() => setAtlasFilter("online")}
                    style={{ fontSize: 10, padding: "3px 8px", borderRadius: 4, border: "1px solid #86efac", background: atlasFilter === "online" ? "#dcfce7" : "#ffffff", color: "#166534", fontWeight: 700, cursor: "pointer" }}
                  >
                    🌐 Reachable Online ({atlasMatrix.online_reachable_count})
                  </button>
                  <button
                    type="button"
                    onClick={() => setAtlasFilter("offline")}
                    style={{ fontSize: 10, padding: "3px 8px", borderRadius: 4, border: "1px solid #fde68a", background: atlasFilter === "offline" ? "#fef3c7" : "#ffffff", color: "#92400e", fontWeight: 700, cursor: "pointer" }}
                  >
                    🏛️ Pre-Digitization Archives ({atlasMatrix.offline_archives_count})
                  </button>
                  <button
                    type="button"
                    onClick={() => setAtlasFilter("id_gated")}
                    style={{ fontSize: 10, padding: "3px 8px", borderRadius: 4, border: "1px solid #e2e8f0", background: atlasFilter === "id_gated" ? "#e2e8f0" : "#ffffff", color: "#334155", fontWeight: 700, cursor: "pointer" }}
                  >
                    🔒 ID / Meter Gated ({atlasMatrix.id_required_count})
                  </button>
                </div>
              </div>
            </div>

            {/* Repositories Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 10 }}>
              {(atlasFilter === "all" ? [...atlasMatrix.online_reachable, ...atlasMatrix.id_required_portals, ...atlasMatrix.offline_archives] :
                atlasFilter === "online" ? atlasMatrix.online_reachable :
                atlasFilter === "offline" ? atlasMatrix.offline_archives :
                atlasMatrix.id_required_portals
              ).map((repo: PublicRecordRepository, idx: number) => (
                <div key={idx} style={{ background: "#ffffff", border: repo.is_custom ? "1px solid #f59e0b" : "1px solid var(--border)", borderRadius: 6, padding: "10px 12px", display: "flex", flexDirection: "column", justifyContent: "space-between", gap: 6 }}>
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 6, marginBottom: 4 }}>
                      <div>
                        <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>
                          {repo.category_name}
                        </span>
                        {repo.is_custom && (
                          <span style={{ marginLeft: 6, fontSize: 9, fontWeight: 800, background: "#fef3c7", color: "#92400e", padding: "1px 5px", borderRadius: 4, border: "1px solid #fde68a" }}>
                            ⭐ Tested Custom
                          </span>
                        )}
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <span style={{ fontSize: 9, fontWeight: 800, textTransform: "uppercase", padding: "1px 5px", borderRadius: 4, background: repo.digitization_status.includes("open") ? "#dcfce7" : repo.digitization_status.includes("offline") ? "#fef3c7" : "#e0e7ff", color: repo.digitization_status.includes("open") ? "#15803d" : repo.digitization_status.includes("offline") ? "#92400e" : "#3730a3" }}>
                          {repo.digitization_status.replace(/_/g, " ")}
                        </span>
                        {repo.is_custom && (
                          <button
                            type="button"
                            onClick={() => handleDeleteRepo(repo.category_id, repo.category_name)}
                            title="Delete custom repository"
                            style={{ background: "transparent", border: "none", cursor: "pointer", fontSize: 12, padding: "0 2px" }}
                          >
                            🗑️
                          </button>
                        )}
                      </div>
                    </div>

                    <div style={{ fontSize: 10, color: "#475569", marginBottom: 4, lineHeight: 1.35 }}>
                      ⏱️ <strong>Digitization Horizon:</strong> {repo.online_since_year ? `Online since ${repo.online_since_year}` : "Strictly physical archive"}
                      {repo.offline_cutoff_year ? ` (Records prior to ${repo.offline_cutoff_year} are only in physical record room)` : ""}
                    </div>

                    {repo.pre_digitization_reason && (
                      <div style={{ fontSize: 10, color: "#991b1b", background: "#fef2f2", padding: "3px 6px", borderRadius: 4, marginBottom: 4 }}>
                        ⚠️ {repo.pre_digitization_reason}
                      </div>
                    )}

                    <div style={{ fontSize: 10, color: "#334155", marginBottom: 3 }}>
                      📍 <strong>Offline Repository:</strong> {repo.offline_repository_name}
                    </div>
                    <div style={{ fontSize: 10, color: "#475569", marginBottom: 3 }}>
                      👤 <strong>Custodian:</strong> {repo.offline_custodian}
                    </div>
                    <div style={{ fontSize: 9, color: "#1e3a8a", background: "#eff6ff", padding: "3px 5px", borderRadius: 4 }}>
                      📜 <strong>Statutory Route:</strong> {repo.offline_retrieval_method}
                    </div>

                    {repo.required_identifiers && repo.required_identifiers.length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
                        {repo.required_identifiers.map((id, i) => (
                          <span key={i} style={{ fontSize: 9, background: "#f1f5f9", color: "#475569", padding: "1px 5px", borderRadius: 3, border: "1px solid #cbd5e1" }}>
                            🔑 {id}
                          </span>
                        ))}
                      </div>
                    )}

                    {repo.operational_warnings && repo.operational_warnings.length > 0 && (
                      <div style={{ marginTop: 4, display: "flex", flexDirection: "column", gap: 3 }}>
                        {repo.operational_warnings.map((warn, wi) => (
                          <div key={wi} style={{ fontSize: 9, color: "#9a3412", background: "#fff7ed", padding: "3px 6px", borderRadius: 4, border: "1px solid #fed7aa" }}>
                            💡 <strong>Learned Caveat:</strong> {warn}
                          </div>
                        ))}
                      </div>
                    )}

                    {((repo.success_count ?? 0) > 0 || (repo.failure_count ?? 0) > 0) && (
                      <div style={{ fontSize: 9, color: "#64748b", marginTop: 4 }}>
                        📊 Empirical: {repo.success_count || 0} hits / {repo.failure_count || 0} dead-ends
                      </div>
                    )}
                  </div>

                  {repo.portal_url && (
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 4, borderTop: "1px dashed var(--border)", marginTop: 4 }}>
                      <a
                        href={repo.portal_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ fontSize: 10, color: "var(--primary)", textDecoration: "underline" }}
                      >
                        🌐 Official Portal ↗
                      </a>
                      {repo.custom_search_query && (
                        <a
                          href={`https://www.google.com/search?q=${encodeURIComponent(repo.custom_search_query)}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-ghost"
                          style={{ fontSize: 9, padding: "2px 6px", textDecoration: "none" }}
                        >
                          🔍 Search Portal ↗
                        </a>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}


        {inquiries.length === 0 ? (
          <div style={{ padding: "24px", textAlign: "center", color: "var(--muted)", fontSize: 13, border: "1px dashed var(--border)", borderRadius: 8 }}>
            No deductive inquiries generated yet. Click &quot;⚡ Auto-Deduce Hypotheses&quot; to derive the public paper trails required by {profile.name}&apos;s milestones.
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: 14 }}>
            {inquiries.map(inq => {
              const meta = INQUIRY_DOMAIN_META[inq.domain] || INQUIRY_DOMAIN_META.general;
              const isProbing = probingInquiryId === inq.inquiry_id;

              return (
                <div
                  key={inq.inquiry_id}
                  style={{
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: inq.status === "confirmed" ? "#f0fdf4" : inq.status === "probed" ? "#f8fafc" : "#ffffff",
                    padding: "14px 16px",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    gap: 10,
                  }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 4, background: meta.bg, color: meta.color }}>
                        {meta.icon} {meta.label}
                      </span>
                      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 800,
                            textTransform: "uppercase",
                            padding: "2px 6px",
                            borderRadius: 4,
                            background:
                              inq.status === "confirmed" ? "#dcfce7" :
                              inq.status === "probed" ? "#e0e7ff" :
                              inq.status === "unarchived_offline" ? "#f1f5f9" : "#fef9c3",
                            color:
                              inq.status === "confirmed" ? "#15803d" :
                              inq.status === "probed" ? "#4338ca" :
                              inq.status === "unarchived_offline" ? "#64748b" : "#a16207",
                          }}
                        >
                          {inq.status}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleDeleteInquiry(inq.inquiry_id)}
                          style={{ background: "none", border: "none", color: "var(--muted)", cursor: "pointer", fontSize: 13 }}
                          title="Remove inquiry"
                        >
                          ✕
                        </button>
                      </div>
                    </div>

                    <div>
                      <h4 style={{ fontSize: 14, fontWeight: 800, margin: "0 0 6px", color: "#0f172a" }}>
                        {inq.fact_anchor}
                      </h4>
                      <div style={{ background: "#f1f5f9", borderLeft: "3px solid #6366f1", padding: "8px 10px", borderRadius: "0 6px 6px 0", fontSize: 12, color: "#1e1b4b", fontStyle: "italic", lineHeight: 1.4 }}>
                        &quot;{inq.deductive_question}&quot;
                      </div>
                    </div>

                    {/* Expected Public Paper Trails Checklist */}
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", marginBottom: 4 }}>
                        Expected Public Paper Trails:
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                        {inq.expected_paper_trails.map((pt, idx) => (
                          <div key={idx} style={{ fontSize: 11, display: "flex", alignItems: "flex-start", gap: 6, color: "#334155" }}>
                            <span style={{ color: "#6366f1" }}>•</span>
                            <span>{pt}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Dual-Track Paper Trail: Digital Probing vs. Physical Archive */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 10, marginTop: 4 }}>
                      {/* 🌐 Digital Track */}
                      <div style={{ background: "#f8fafc", padding: "8px 10px", borderRadius: 6, border: "1px solid #e2e8f0" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "#1e293b", display: "flex", alignItems: "center", gap: 4 }}>
                            🌐 Digital Track
                          </span>
                          <span
                            style={{
                              fontSize: 9,
                              fontWeight: 700,
                              textTransform: "uppercase",
                              padding: "1px 6px",
                              borderRadius: 4,
                              background:
                                inq.online_probe_status === "confirmed" ? "#dcfce7" :
                                inq.online_probe_status === "probed" ? "#e0e7ff" : "#f1f5f9",
                              color:
                                inq.online_probe_status === "confirmed" ? "#166534" :
                                inq.online_probe_status === "probed" ? "#3730a3" : "#64748b",
                            }}
                          >
                            {inq.online_probe_status || "open"}
                          </span>
                        </div>

                        {inq.probe_queries && inq.probe_queries.length > 0 && (
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 6 }}>
                            {inq.probe_queries.slice(0, 3).map((q, idx) => (
                              <a
                                key={idx}
                                href={`https://www.google.com/search?q=${encodeURIComponent(q)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn-ghost"
                                style={{ fontSize: 10, padding: "2px 6px", textDecoration: "none", color: "var(--primary)" }}
                                title={`Query: ${q}`}
                              >
                                🔍 {q.slice(0, 28)}… ↗
                              </a>
                            ))}
                          </div>
                        )}

                        {inq.corroborating_links && inq.corroborating_links.length > 0 && (
                          <div style={{ marginTop: 6, paddingTop: 6, borderTop: "1px dashed #cbd5e1" }}>
                            <div style={{ fontSize: 10, fontWeight: 700, color: "#15803d", marginBottom: 3 }}>
                              ✓ Corroborated Online Links ({inq.corroborating_links.length}):
                            </div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                              {inq.corroborating_links.map((link, idx) => (
                                <a
                                  key={idx}
                                  href={link}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{
                                    fontSize: 10,
                                    color: "#0369a1",
                                    textDecoration: "underline",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                  }}
                                >
                                  🔗 {link}
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* 🏛️ Physical Archive Track */}
                      <div style={{ background: "#fffbeb", padding: "8px 10px", borderRadius: 6, border: "1px solid #fef3c7" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "#92400e", display: "flex", alignItems: "center", gap: 4 }}>
                            🏛️ Physical Archive Track
                          </span>
                          <span
                            style={{
                              fontSize: 9,
                              fontWeight: 700,
                              textTransform: "uppercase",
                              padding: "1px 6px",
                              borderRadius: 4,
                              background: "#fef3c7",
                              color: "#b45309",
                            }}
                          >
                            Offline Repository
                          </span>
                        </div>

                        {inq.offline_archive_location && (
                          <div style={{ fontSize: 11, color: "#451a03", marginBottom: 4, lineHeight: 1.35 }}>
                            <strong>📍 Location:</strong> {inq.offline_archive_location}
                          </div>
                        )}
                        {inq.offline_custodian && (
                          <div style={{ fontSize: 11, color: "#78350f", marginBottom: 4, lineHeight: 1.35 }}>
                            <strong>👤 Custodian:</strong> {inq.offline_custodian}
                          </div>
                        )}
                        {inq.offline_retrieval_method && (
                          <div
                            style={{
                              fontSize: 10,
                              color: "#92400e",
                              background: "rgba(245, 158, 11, 0.12)",
                              padding: "5px 7px",
                              borderRadius: 4,
                              marginTop: 4,
                              lineHeight: 1.35,
                            }}
                          >
                            <strong>📜 Statutory Retrieval:</strong> {inq.offline_retrieval_method}
                          </div>
                        )}
                      </div>
                    </div>

                    {inq.findings_summary && (
                      <div style={{ fontSize: 11, background: "rgba(99, 102, 241, 0.08)", border: "1px solid rgba(99, 102, 241, 0.2)", padding: "6px 8px", borderRadius: 4, color: "#312e81", marginTop: 4 }}>
                        📌 <strong>Deductive Finding:</strong> {inq.findings_summary}
                      </div>
                    )}

                    {(inq.learned_lesson || inq.failure_reason) && (
                      <div style={{ background: "#fff7ed", border: "1px solid #fed7aa", borderRadius: 6, padding: "8px 10px", marginTop: 4 }}>
                        {inq.learned_lesson && (
                          <div style={{ fontSize: 11, color: "#9a3412", lineHeight: 1.35 }}>
                            💡 <strong>Learned Lesson:</strong> {inq.learned_lesson}
                          </div>
                        )}
                        {inq.failure_reason && (
                          <div style={{ fontSize: 10, color: "#b45309", marginTop: 3, borderTop: inq.learned_lesson ? "1px dashed #fed7aa" : "none", paddingTop: inq.learned_lesson ? 3 : 0 }}>
                            ⛔ <strong>Dead-End ({inq.failure_mode?.replace(/_/g, " ")}):</strong> {inq.failure_reason}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 8, borderTop: "1px solid var(--border)", marginTop: 6, gap: 6, flexWrap: "wrap" }}>
                    <div style={{ display: "flex", gap: 4, alignItems: "center", flexWrap: "wrap" }}>
                      <button
                        type="button"
                        onClick={() => handleUpdateInquiryStatus(inq.inquiry_id, "confirmed")}
                        style={{
                          fontSize: 10,
                          padding: "2px 6px",
                          borderRadius: 4,
                          border: "1px solid #86efac",
                          background: inq.status === "confirmed" ? "#dcfce7" : "#ffffff",
                          color: "#15803d",
                          fontWeight: 700,
                          cursor: "pointer",
                        }}
                      >
                        ✓ Confirmed
                      </button>
                      <button
                        type="button"
                        onClick={() => handleUpdateInquiryStatus(inq.inquiry_id, "unarchived_offline")}
                        style={{
                          fontSize: 10,
                          padding: "2px 6px",
                          borderRadius: 4,
                          border: "1px solid var(--border)",
                          background: inq.status === "unarchived_offline" ? "#f1f5f9" : "#ffffff",
                          color: "var(--muted)",
                          cursor: "pointer",
                        }}
                      >
                        Offline / Physical
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setFailureModalInquiry(inq);
                          setFailureMode(inq.failure_mode || "pre_digitization_cutoff");
                          setFailureReason(inq.failure_reason || "");
                          setFailureLesson(inq.learned_lesson || "");
                          setFailureRepoId("");
                        }}
                        style={{
                          fontSize: 10,
                          padding: "2px 6px",
                          borderRadius: 4,
                          border: "1px solid #fde68a",
                          background: inq.status === "dead_end" ? "#fef3c7" : "#ffffff",
                          color: "#92400e",
                          fontWeight: 700,
                          cursor: "pointer",
                        }}
                        title="Log a failed probe or dead-end and teach the system how to adapt"
                      >
                        ⚠️ Log Failure / Lesson
                      </button>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleProbeInquiry(inq.inquiry_id)}
                      disabled={isProbing}
                      style={{
                        fontSize: 11,
                        padding: "3px 8px",
                        borderRadius: 4,
                        background: "#6366f1",
                        color: "#ffffff",
                        border: "none",
                        cursor: "pointer",
                        fontWeight: 600,
                      }}
                    >
                      {isProbing ? "Probing Archives…" : "🔍 Probe Archives"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Section 3: Auxiliary Leads Stream (Public Records & Corroborating Clues) */}
      <div className="card" style={{ padding: "18px 20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10, marginBottom: 14 }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: 0 }}>
              Auxiliary Leads &amp; Public Records Stream
            </h3>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: "3px 0 0" }}>
              Helping documents, theses, grant sanctions, and gazettes supporting forensic background verification.
            </p>
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            {/* Search Input */}
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="🔍 Search leads / queries…"
              aria-label="Search auxiliary leads"
              style={{ fontSize: 12, padding: "6px 10px", width: 180 }}
            />

            {/* Category Filter */}
            <select
              value={categoryFilter}
              onChange={e => setCategoryFilter(e.target.value)}
              aria-label="Filter lead category"
              style={{ fontSize: 12, padding: "6px 8px" }}
            >
              <option value="all">All Categories</option>
              <option value="thesis_dissertation">🎓 Shodhganga Theses</option>
              <option value="grant_sanction">💰 Grants &amp; Budget</option>
              <option value="recruitment_notice">📋 Fellows &amp; Vacancies</option>
              <option value="annual_report">📑 Annual Reports</option>
              <option value="electoral_gazette">📍 Electoral &amp; Housing</option>
              <option value="legal_tribunal">⚖️ CAT / Tribunals</option>
            </select>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value as any)}
              aria-label="Filter lead status"
              style={{ fontSize: 12, padding: "6px 8px" }}
            >
              <option value="all">All Statuses</option>
              <option value="lead">🟡 Active Leads</option>
              <option value="corroborated">🟢 Corroborated</option>
              <option value="inspected">🔵 Inspected</option>
              <option value="dead_end">⚪ Dead Ends</option>
            </select>
          </div>
        </div>

        {filteredLeads.length === 0 ? (
          <div style={{ padding: "28px", textAlign: "center", color: "var(--muted)", fontSize: 13, border: "1px dashed var(--border)", borderRadius: 8 }}>
            No auxiliary leads found matching the filters. Click &quot;⚡ Run Public Records Sweep&quot; to auto-generate queries.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {filteredLeads.map(lead => {
              const catMeta = LEAD_CATEGORY_META[lead.category] || LEAD_CATEGORY_META.general_lead;
              const associatedPivot = pivots.find(p => p.pivot_id === lead.pivot_id);

              return (
                <div
                  key={lead.lead_id}
                  style={{
                    padding: "14px 16px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: lead.status === "corroborated" ? "#f0fdf4" : "#ffffff",
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10, flexWrap: "wrap" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          padding: "2px 7px",
                          borderRadius: 4,
                          background: catMeta.badge,
                          color: "#1e293b",
                        }}
                      >
                        {catMeta.icon} {catMeta.label}
                      </span>

                      {associatedPivot && (
                        <span style={{ fontSize: 11, color: "var(--muted)", background: "#f8fafc", border: "1px solid var(--border)", padding: "1px 6px", borderRadius: 4 }}>
                          Pivot: <strong>{associatedPivot.title}</strong>
                        </span>
                      )}

                      {/* Status Tag */}
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 800,
                          textTransform: "uppercase",
                          padding: "2px 6px",
                          borderRadius: 4,
                          background:
                            lead.status === "corroborated" ? "#dcfce7" :
                            lead.status === "inspected" ? "#e0e7ff" :
                            lead.status === "dead_end" ? "#f1f5f9" : "#fef9c3",
                          color:
                            lead.status === "corroborated" ? "#15803d" :
                            lead.status === "inspected" ? "#4338ca" :
                            lead.status === "dead_end" ? "#64748b" : "#a16207",
                        }}
                      >
                        {lead.status}
                      </span>

                      {/* Subject Mention Badge */}
                      {lead.has_subject_mention && (
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 800,
                            padding: "2px 6px",
                            borderRadius: 4,
                            background: "#fef3c7",
                            color: "#92400e",
                            border: "1px solid #fde68a",
                          }}
                          title="Document directly names the biographical subject"
                        >
                          🏷️ Names Subject
                        </span>
                      )}

                      {/* Promoted to Source Badge */}
                      {lead.promoted_source_id && (
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 800,
                            padding: "2px 6px",
                            borderRadius: 4,
                            background: "#dcfce7",
                            color: "#166534",
                            border: "1px solid #86efac",
                          }}
                          title="Promoted to primary Wikipedia Sources list"
                        >
                          ✓ Wiki Source
                        </span>
                      )}
                    </div>

                    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      {/* 1-Click Promote to Primary Wiki Source */}
                      {lead.url && !lead.promoted_source_id && (
                        <button
                          type="button"
                          onClick={() => handlePromoteLead(lead.lead_id)}
                          disabled={promotingId === lead.lead_id}
                          style={{
                            fontSize: 11,
                            padding: "2px 8px",
                            borderRadius: 4,
                            border: "1px solid #f59e0b",
                            background: lead.has_subject_mention ? "#f59e0b" : "#fffbeb",
                            color: lead.has_subject_mention ? "#ffffff" : "#b45309",
                            fontWeight: 700,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: 3,
                          }}
                          title="Promote this verified record to primary Wikipedia sources for claim extraction and wikitext citation"
                        >
                          {promotingId === lead.lead_id ? "Promoting…" : "⭐ Promote to Wiki Source ➡️"}
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => handleUpdateLeadStatus(lead.lead_id, "corroborated")}
                        style={{
                          fontSize: 11,
                          padding: "2px 8px",
                          borderRadius: 4,
                          border: "1px solid #86efac",
                          background: lead.status === "corroborated" ? "#dcfce7" : "#ffffff",
                          color: "#15803d",
                          fontWeight: 700,
                          cursor: "pointer",
                        }}
                        title="Mark as corroborated evidentiary record"
                      >
                        ✓ Corroborated
                      </button>
                      <button
                        type="button"
                        onClick={() => handleUpdateLeadStatus(lead.lead_id, "inspected")}
                        style={{
                          fontSize: 11,
                          padding: "2px 8px",
                          borderRadius: 4,
                          border: "1px solid var(--border)",
                          background: lead.status === "inspected" ? "#e0e7ff" : "#ffffff",
                          color: "#374151",
                          cursor: "pointer",
                        }}
                      >
                        Inspected
                      </button>
                      <button
                        type="button"
                        onClick={() => handleUpdateLeadStatus(lead.lead_id, "dead_end")}
                        style={{
                          fontSize: 11,
                          padding: "2px 8px",
                          borderRadius: 4,
                          border: "1px solid var(--border)",
                          background: lead.status === "dead_end" ? "#f1f5f9" : "#ffffff",
                          color: "var(--muted)",
                          cursor: "pointer",
                        }}
                      >
                        Dead End
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteLead(lead.lead_id)}
                        style={{ background: "none", border: "none", color: "var(--muted)", cursor: "pointer", fontSize: 13 }}
                        title="Delete lead"
                      >
                        ✕
                      </button>
                    </div>
                  </div>

                  <div>
                    <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 4px" }}>
                      {lead.title}
                    </h4>
                    {lead.lead_notes && (
                      <p style={{ fontSize: 12, color: "var(--text)", margin: "0 0 6px", lineHeight: 1.4 }}>
                        💡 <strong>Forensic Clue:</strong> {lead.lead_notes}
                      </p>
                    )}
                    {lead.source_snippet && (
                      <div style={{ fontSize: 12, fontStyle: "italic", background: "rgba(0,0,0,0.03)", padding: "6px 10px", borderRadius: 4, marginBottom: 6 }}>
                        &ldquo;{lead.source_snippet}&rdquo;
                      </div>
                    )}
                  </div>

                  {/* Reproducible Search Query or URL */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8, background: "#f8fafc", padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)" }}>
                    <div style={{ flex: 1, minWidth: 200 }}>
                      {lead.url ? (
                        <a
                          href={safeHref(lead.url)}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ fontSize: 12, color: "var(--primary)", fontWeight: 600, wordBreak: "break-all" }}
                        >
                          {lead.url} ↗
                        </a>
                      ) : lead.automated_query ? (
                        <code style={{ fontSize: 11, fontFamily: "monospace", color: "#1e40af" }}>
                          Query: {lead.automated_query}
                        </code>
                      ) : (
                        <span style={{ fontSize: 11, color: "var(--muted)" }}>Manual Lead Anchor</span>
                      )}
                    </div>

                    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      {lead.automated_query && (
                        <a
                          href={`https://www.google.com/search?q=${encodeURIComponent(lead.automated_query)}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-ghost"
                          style={{ fontSize: 11, padding: "2px 8px", textDecoration: "none", color: "var(--primary)" }}
                        >
                          Google Query ↗
                        </a>
                      )}
                      <span style={{ fontSize: 10, color: "var(--muted)" }}>
                        Logged by {lead.actor_logged === "agent" ? "🤖 Agent" : "👤 Human"}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Pivot Modal */}
      {showAddPivot && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: "fixed",
            top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
          onClick={() => setShowAddPivot(false)}
        >
          <div className="card" style={{ maxWidth: 520, width: "100%", padding: "20px" }} onClick={e => e.stopPropagation()}>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: "0 0 12px" }}>+ Add Investigation Pivot</h3>
            <form onSubmit={handleAddPivotSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Pivot Type</label>
                <select value={pivotType} onChange={e => setPivotType(e.target.value)} style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}>
                  <option value="project_grant">🔬 Project &amp; Grant Scheme</option>
                  <option value="institution">🏛️ Research Institution / Workplace</option>
                  <option value="location">📍 Spatial / Residential Campus</option>
                  <option value="associate">👥 Recruited Fellows &amp; Co-Actors</option>
                  <option value="gazette_legal">⚖️ Gazette &amp; Tribunal Records</option>
                  <option value="family_social">🏡 Domestic &amp; Campus Schooling</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Title / Name</label>
                <input
                  value={pivotTitle}
                  onChange={e => setPivotTitle(e.target.value)}
                  placeholder="e.g. Project Hisar Gaurav (Cloning Scheme)"
                  required
                  style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Context / Description</label>
                <textarea
                  value={pivotDesc}
                  onChange={e => setPivotDesc(e.target.value)}
                  placeholder="e.g. Buffalo cloning scheme funded by ICAR-NASF/DBT at CIRB"
                  style={{ width: "100%", height: 60, padding: "7px 10px", fontSize: 13, resize: "vertical" }}
                />
              </div>

              <div style={{ display: "flex", gap: 10 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Time Period</label>
                  <input
                    value={pivotTime}
                    onChange={e => setPivotTime(e.target.value)}
                    placeholder="e.g. 2014–2018"
                    style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Location</label>
                  <input
                    value={pivotLocation}
                    onChange={e => setPivotLocation(e.target.value)}
                    placeholder="e.g. Hisar, Haryana"
                    style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Associated Entities (comma separated)</label>
                <input
                  value={pivotEntities}
                  onChange={e => setPivotEntities(e.target.value)}
                  placeholder="e.g. ICAR-CIRB, NASF, Dr Inderjeet Singh"
                  style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 10 }}>
                <button type="button" className="btn-ghost" onClick={() => setShowAddPivot(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Add Pivot Anchor</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Lead Modal */}
      {showAddLead && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: "fixed",
            top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
          onClick={() => setShowAddLead(false)}
        >
          <div className="card" style={{ maxWidth: 520, width: "100%", padding: "20px" }} onClick={e => e.stopPropagation()}>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: "0 0 12px" }}>+ Log Auxiliary Lead</h3>
            <form onSubmit={handleAddLeadSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Lead Category</label>
                <select value={leadCategory} onChange={e => setLeadCategory(e.target.value)} style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}>
                  <option value="thesis_dissertation">🎓 Shodhganga Theses</option>
                  <option value="grant_sanction">💰 Grants &amp; Budget</option>
                  <option value="recruitment_notice">📋 Fellows &amp; Vacancies</option>
                  <option value="annual_report">📑 Annual Reports</option>
                  <option value="electoral_gazette">📍 Electoral &amp; Housing</option>
                  <option value="legal_tribunal">⚖️ CAT / Tribunals</option>
                  <option value="general_lead">🔍 General Lead</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Title</label>
                <input
                  value={leadTitle}
                  onChange={e => setLeadTitle(e.target.value)}
                  placeholder="e.g. CIRB 2016 Annual Report Division Staff Roster"
                  required
                  style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Document URL (optional)</label>
                <input
                  value={leadUrl}
                  onChange={e => setLeadUrl(e.target.value)}
                  placeholder="https://..."
                  style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Connect to Pivot (optional)</label>
                <select value={leadPivotId} onChange={e => setLeadPivotId(e.target.value)} style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}>
                  <option value="">-- No specific pivot --</option>
                  {pivots.map(p => (
                    <option key={p.pivot_id} value={p.pivot_id}>{p.title}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Lead Notes / Clues</label>
                <textarea
                  value={leadNotes}
                  onChange={e => setLeadNotes(e.target.value)}
                  placeholder="What specific question does this document help resolve?"
                  style={{ width: "100%", height: 60, padding: "7px 10px", fontSize: 13, resize: "vertical" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 10 }}>
                <button type="button" className="btn-ghost" onClick={() => setShowAddLead(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Save Lead</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Custom Inquiry Modal */}
      {showAddInquiry && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: "fixed",
            top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
          onClick={() => setShowAddInquiry(false)}
        >
          <div className="card" style={{ maxWidth: 560, width: "100%", padding: "20px" }} onClick={e => e.stopPropagation()}>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: "0 0 4px", display: "flex", alignItems: "center", gap: 6 }}>
              <span>🧠</span> Formulate Deductive Paper Trail Inquiry
            </h3>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 14px" }}>
              Given an established biographical milestone, what official public records must necessarily exist?
            </p>
            <form onSubmit={handleAddInquirySubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Fact Anchor (Milestone)</label>
                <input
                  value={inqAnchor}
                  onChange={e => setInqAnchor(e.target.value)}
                  placeholder="e.g. B.Sc. from CCS Haryana Agricultural University (HAU) in 1985"
                  required
                  style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Inquiry Domain</label>
                  <select value={inqDomain} onChange={e => setInqDomain(e.target.value)} style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}>
                    <option value="academic_degree">🎓 Undergraduate / Master's</option>
                    <option value="doctoral_thesis">📜 Ph.D. Dissertation Deposit</option>
                    <option value="service_entry">🏛️ ARS / Public Service Gazette</option>
                    <option value="research_grant">💰 Extramural Grant Sanction</option>
                    <option value="campus_quarters">🏡 Staff Quarters / Voter List</option>
                    <option value="superannuation">🚪 Superannuation / Relinquishment</option>
                    <option value="general">🔍 General Inquiry</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>
                  Deductive Question ("If True, What Must Exist?")
                </label>
                <textarea
                  value={inqQuestion}
                  onChange={e => setInqQuestion(e.target.value)}
                  placeholder="e.g. If a student graduated B.Sc. from HAU in 1985, what convocation gazette, exam notification, or silver jubilee reunion souvenir exists in university archives?"
                  required
                  style={{ width: "100%", height: 60, padding: "7px 10px", fontSize: 13, resize: "vertical" }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>
                  Expected Public Paper Trails (one per line)
                </label>
                <textarea
                  value={inqPaperTrails}
                  onChange={e => setInqPaperTrails(e.target.value)}
                  placeholder="CCS HAU 1985 Convocation Souvenir Booklet&#10;College of Veterinary Sciences 1985 Graduate Roster&#10;Nehru Library Physical Archives at Hisar"
                  style={{ width: "100%", height: 65, padding: "7px 10px", fontSize: 13, resize: "vertical" }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>
                  Archive Probe Queries (one per line)
                </label>
                <textarea
                  value={inqQueries}
                  onChange={e => setInqQueries(e.target.value)}
                  placeholder="&quot;CCS HAU&quot; &quot;1985&quot; &quot;Prem Singh Yadav&quot;&#10;site:krishikosh.egranth.ac.in &quot;Prem Singh Yadav&quot; &quot;HAU&quot;"
                  style={{ width: "100%", height: 50, padding: "7px 10px", fontSize: 13, resize: "vertical" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
                <button type="button" className="btn-ghost" onClick={() => setShowAddInquiry(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Register Inquiry</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Custom Tested Repository Modal */}
      {showAddRepo && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: "fixed",
            top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
          onClick={() => setShowAddRepo(false)}
        >
          <div className="card" style={{ maxWidth: 640, width: "100%", maxHeight: "90vh", overflowY: "auto", padding: "20px" }} onClick={e => e.stopPropagation()}>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: "0 0 4px", display: "flex", alignItems: "center", gap: 6 }}>
              <span>🗺️</span> Register Tested Public Records Repository
            </h3>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 14px" }}>
              Permanently catalog a tested open or physical repository into the master Atlas. It will automatically assist future investigations for any subject in this jurisdiction.
            </p>
            <form onSubmit={handleAddRepoSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Repository / Portal Name *</label>
                <input
                  value={repoName}
                  onChange={e => setRepoName(e.target.value)}
                  placeholder="e.g. Punjab Land Records Society (PLRS / Fard Jamabandi)"
                  required
                  style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Domain</label>
                  <select value={repoDomain} onChange={e => setRepoDomain(e.target.value)} style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}>
                    <option value="civic_electoral">🗳️ Civic &amp; Electoral Rolls</option>
                    <option value="utility_electricity">⚡ Electricity &amp; Utility Discom</option>
                    <option value="land_revenue">🌾 Land Revenue &amp; Jamabandi / Bhulekh</option>
                    <option value="municipal_property">🏢 Municipal Property &amp; House Tax</option>
                    <option value="gazette_official">📜 Official Gazette &amp; Notifications</option>
                    <option value="pension_service">🎖️ Pension &amp; Civil Service (CPAO / SPARSH)</option>
                    <option value="judicial_litigation">⚖️ Judicial &amp; Case Filings (eCourts)</option>
                    <option value="academic_thesis">🎓 Academic Theses (KrishiKosh / Shodhganga)</option>
                    <option value="academic_profile">🔬 Scholar Directory (Vidwan / IRINS)</option>
                    <option value="patent_registry">💡 Patent &amp; IP Office (InPASS)</option>
                    <option value="professional_council">🩺 Professional Council (Medical / Bar)</option>
                    <option value="corporate_registry">🏛️ Corporate Registry (MCA21 / RoC)</option>
                    <option value="general_public_record">📁 General Public Record</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Jurisdiction Level</label>
                  <select value={repoJurisdiction} onChange={e => setRepoJurisdiction(e.target.value)} style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}>
                    <option value="national">Central / All-India</option>
                    <option value="state">State Level</option>
                    <option value="district">District / Municipal Level</option>
                    <option value="institutional">Autonomous Institution</option>
                  </select>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>State / UT</label>
                  <input
                    value={repoState}
                    onChange={e => setRepoState(e.target.value)}
                    placeholder="e.g. Punjab, Haryana, Uttar Pradesh, Central"
                    style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>District / City (Optional)</label>
                  <input
                    value={repoDistrict}
                    onChange={e => setRepoDistrict(e.target.value)}
                    placeholder="e.g. Ludhiana, Hisar, Lucknow, Pune"
                    style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Digitization Status</label>
                  <select value={repoDigitizationStatus} onChange={e => setRepoDigitizationStatus(e.target.value)} style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}>
                    <option value="digitized_open_search">🌐 Digitized Open</option>
                    <option value="digitized_captcha_gated">🧩 Captcha Gated</option>
                    <option value="digitized_id_required">🔒 ID / Meter Required</option>
                    <option value="retrospectively_scanned_partial">📑 Scanned Partial</option>
                    <option value="strictly_offline_physical">🏛️ Strictly Offline</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Online Since Year</label>
                  <input
                    type="number"
                    value={repoOnlineYear}
                    onChange={e => setRepoOnlineYear(e.target.value)}
                    placeholder="e.g. 2011"
                    style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Pre-Cutoff Year</label>
                  <input
                    type="number"
                    value={repoOfflineCutoff}
                    onChange={e => setRepoOfflineCutoff(e.target.value)}
                    placeholder="e.g. 2010"
                    style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Official Portal URL</label>
                  <input
                    value={repoPortalUrl}
                    onChange={e => setRepoPortalUrl(e.target.value)}
                    placeholder="https://jamabandi.punjab.gov.in"
                    style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Search Query Template</label>
                  <input
                    value={repoSearchTemplate}
                    onChange={e => setRepoSearchTemplate(e.target.value)}
                    placeholder='site:jamabandi.punjab.gov.in "{name}"'
                    style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Offline Physical Archive</label>
                  <input
                    value={repoOfflineName}
                    onChange={e => setRepoOfflineName(e.target.value)}
                    placeholder="District Revenue Record Room (सदर मालखाना)"
                    style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Statutory Custodian</label>
                  <input
                    value={repoOfflineCustodian}
                    onChange={e => setRepoOfflineCustodian(e.target.value)}
                    placeholder="Tehsildar &amp; District Revenue Officer"
                    style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Statutory Retrieval Method (Offline / RTI)</label>
                <input
                  value={repoOfflineMethod}
                  onChange={e => setRepoOfflineMethod(e.target.value)}
                  placeholder="Application for inspection of Jamabandi Registers with Halqa Patwari; or RTI Act Sec 6(1)"
                  style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Required Identifiers (comma-separated)</label>
                <input
                  value={repoIdentifiers}
                  onChange={e => setRepoIdentifiers(e.target.value)}
                  placeholder="Khewat No, Khasra No, Village Name, Father Name"
                  style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Forensic Utility Notes</label>
                <textarea
                  value={repoUtilityNotes}
                  onChange={e => setRepoUtilityNotes(e.target.value)}
                  placeholder="Statutory proof of ancestral land ownership, village domicile, and legal lineage."
                  style={{ width: "100%", height: 50, padding: "7px 10px", fontSize: 13, resize: "vertical" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
                <button type="button" className="btn-ghost" onClick={() => setShowAddRepo(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={savingRepo}>
                  {savingRepo ? "Registering…" : "Register Repository"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Log Failure & Learn from Mistake Modal */}
      {failureModalInquiry && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: "fixed",
            top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
          onClick={() => setFailureModalInquiry(null)}
        >
          <div className="card" style={{ maxWidth: 580, width: "100%", maxHeight: "90vh", overflowY: "auto", padding: "20px" }} onClick={e => e.stopPropagation()}>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: "0 0 4px", display: "flex", alignItems: "center", gap: 6, color: "#991b1b" }}>
              <span>🧠</span> Log Inquiry Failure &amp; Learn from Mistake
            </h3>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 12px" }}>
              Failures and dead-ends are valuable negative knowledge. Recording why this search failed permanently updates the engine and the public records atlas so future sweeps for this and subsequent subjects adapt automatically.
            </p>

            <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, padding: "8px 10px", marginBottom: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#334155" }}>Target Hypothesis:</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#0f172a", marginTop: 2 }}>{failureModalInquiry.fact_anchor}</div>
              <div style={{ fontSize: 11, color: "#64748b", fontStyle: "italic", marginTop: 2 }}>&quot;{failureModalInquiry.deductive_question}&quot;</div>
            </div>

            <form onSubmit={handleLogFailureSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>Failure Mode / Root Cause *</label>
                <select value={failureMode} onChange={e => setFailureMode(e.target.value)} style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}>
                  <option value="pre_digitization_cutoff">🏛️ Pre-Digitization Horizon (Records predating year X exist only in physical paper stacks)</option>
                  <option value="bot_blocked">🤖 Bot / Cloudflare IP Blocked (VM Datacenter IP blocked; requires Indian mobile carrier IP)</option>
                  <option value="captcha_gated">🧩 Captcha / OTP Challenge (Interactive human solve required)</option>
                  <option value="id_gated">🔒 Identifier Gated (Requires private Consumer No, EPIC, or Aadhaar)</option>
                  <option value="not_found">❌ Negative Record (Subject not found under this name / spelling variant)</option>
                  <option value="domain_down">🌐 Portal Offline / Broken Government URL</option>
                  <option value="dead_end">⛔ General Dead-End (Hypothesis contradicted or refuted)</option>
                </select>
              </div>

              {atlasMatrix && (
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>
                    Propagate Lesson to Public Repository Atlas (Optional)
                  </label>
                  <select value={failureRepoId} onChange={e => setFailureRepoId(e.target.value)} style={{ width: "100%", padding: "7px 10px", fontSize: 13 }}>
                    <option value="">Do not attach to a repository (Subject-specific only)</option>
                    {[...atlasMatrix.online_reachable, ...atlasMatrix.id_required_portals, ...atlasMatrix.offline_archives].map((r, i) => (
                      <option key={i} value={r.category_id}>
                        {r.category_name} ({r.category_id})
                      </option>
                    ))}
                  </select>
                  <div style={{ fontSize: 10, color: "var(--muted)", marginTop: 2 }}>
                    Attaching this failure to a repository permanently updates the atlas so the 100th person research automatically avoids this pitfall.
                  </div>
                </div>
              )}

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>
                  What Happened? (Dead-End Details) *
                </label>
                <textarea
                  value={failureReason}
                  onChange={e => setFailureReason(e.target.value)}
                  placeholder="e.g. Scanned archive queries returned 0 results; verified that undergraduate convocation rolls for 1985 were not digitized."
                  required
                  style={{ width: "100%", height: 55, padding: "7px 10px", fontSize: 13, resize: "vertical" }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 4 }}>
                  Learned Lesson / Workaround *
                </label>
                <textarea
                  value={failureLesson}
                  onChange={e => setFailureLesson(e.target.value)}
                  placeholder="e.g. Do not repeat digital queries for pre-1990 degree records; immediately generate offline physical inspection request to Nehru Library archives."
                  required
                  style={{ width: "100%", height: 60, padding: "7px 10px", fontSize: 13, resize: "vertical" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
                <button type="button" className="btn-ghost" onClick={() => setFailureModalInquiry(null)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={loggingFailure} style={{ background: "#dc2626", borderColor: "#b91c1c" }}>
                  {loggingFailure ? "Learning…" : "💾 Save & Learn from Mistake"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
