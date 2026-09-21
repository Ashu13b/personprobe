import type { Source, Claim } from "./types";

export type ThematicCategory =
  | "all"
  | "news"
  | "academic"
  | "biographical"
  | "discarded";

export interface ThematicCategoryMeta {
  id: ThematicCategory;
  label: string;
  icon: string;
  description: string;
  badgeBg: string;
  badgeColor: string;
  badgeBorder: string;
}

export const THEMATIC_CATEGORIES: ThematicCategoryMeta[] = [
  {
    id: "all",
    label: "All Sources",
    icon: "🌐",
    description: "Every active source collected in this research session",
    badgeBg: "#f1f5f9",
    badgeColor: "#334155",
    badgeBorder: "#cbd5e1",
  },
  {
    id: "news",
    label: "Press & Media",
    icon: "📰",
    description: "Independent secondary reporting from news outlets, press, and periodicals",
    badgeBg: "#f0fdfa",
    badgeColor: "#0f766e",
    badgeBorder: "#99f6e4",
  },
  {
    id: "academic",
    label: "Scholarly & Works",
    icon: "📚",
    description: "Authored papers, books, patents, academic journals, and research databases",
    badgeBg: "#eff6ff",
    badgeColor: "#1d4ed8",
    badgeBorder: "#bfdbfe",
  },
  {
    id: "biographical",
    label: "Biographical & Official",
    icon: "🏛️",
    description: "Institutional bio directories, official profiles, awards, and career records",
    badgeBg: "#fdf4ff",
    badgeColor: "#86198f",
    badgeBorder: "#f0abfc",
  },
  {
    id: "discarded",
    label: "Discarded Registry",
    icon: "🗑️",
    description: "Links pruned or rejected with recorded justification and one-click recovery",
    badgeBg: "#fff1f2",
    badgeColor: "#be123c",
    badgeBorder: "#fecdd3",
  },
];

const BIO_FIELDS = new Set([
  "birth_date", "birth_place", "education", "early_life", "full_name",
  "position", "affiliation", "career", "roles", "appointment", "award",
  "honors", "fellowship", "recognition", "nationality",
]);

const NEWS_DOMAIN_PATTERNS = [
  "thehindu.com", "tribuneindia.com", "indianexpress.com", "timesofindia.indiatimes.com",
  "theprint.in", "amarujala.com", "jagran.com", "millenniumpost.in", "hindustantimes.com",
  "bhaskar.com", "news18.com", "ndtv.com", "ddnews.gov.in", "business-standard.com",
  "livemint.com", "aninews.in", "ptinews.com", "citytehelka.in", "bbc.com", "reuters.com",
  "theguardian.com", "apnews.com", "nytimes.com", "washingtonpost.com", "bloomberg.com",
  "forbes.com", "nature.com/articles/d", "economist.com",
];

export function getSourceCategories(source: Source, attachedClaims: Claim[]): ThematicCategory[] {
  const cats = new Set<ThematicCategory>();

  // 1. Press & Media
  const isNewsDomain = NEWS_DOMAIN_PATTERNS.some(d => source.url.toLowerCase().includes(d));
  if (source.provenance_category === "independent_secondary" || isNewsDomain) {
    cats.add("news");
  }

  // 2. Scholarly & Works
  const isAcademic =
    source.provenance_category === "authored_publication" ||
    (source.all_paper_authors && source.all_paper_authors.length > 0) ||
    source.fetched_by === "semantic_scholar" ||
    source.url.includes("doi.org") ||
    source.url.includes("scholar.google") ||
    source.url.includes("scopus.com") ||
    source.url.includes("arxiv.org") ||
    source.url.includes("researchgate.net/publication");

  if (isAcademic) {
    cats.add("academic");
  }

  // 3. Biographical & Official
  const hasBioClaim = attachedClaims.some(c => BIO_FIELDS.has(c.field.toLowerCase()));
  const isBioDirectory =
    source.provenance_category === "institutional_bio" ||
    [".edu", ".ac.in", ".res.in", ".gov.in", "orcid.org", "researchgate.net/profile", "wikipedia.org", "wikidata.org"].some(d =>
      source.url.toLowerCase().includes(d)
    );

  if (hasBioClaim || isBioDirectory) {
    cats.add("biographical");
  }

  return Array.from(cats);
}

export function computeCategoryCounts(
  sources: Source[],
  claims: Claim[],
  _personName: string,
  discardedCount: number
): Record<ThematicCategory, number> {
  const claimsByUrl = new Map<string, Claim[]>();
  for (const c of claims) {
    if (c.source_url) {
      const list = claimsByUrl.get(c.source_url) ?? [];
      list.push(c);
      claimsByUrl.set(c.source_url, list);
    }
  }

  const counts: Record<ThematicCategory, number> = {
    all: sources.length,
    news: 0,
    academic: 0,
    biographical: 0,
    discarded: discardedCount,
  };

  for (const s of sources) {
    const attached = claimsByUrl.get(s.url) ?? [];
    const cats = getSourceCategories(s, attached);
    for (const cat of cats) {
      if (cat in counts) {
        counts[cat]++;
      }
    }
  }

  return counts;
}

export function filterSources(
  sources: Source[],
  claims: Claim[],
  _personName: string,
  selectedCategory: ThematicCategory,
  searchQuery: string,
  filterLiveness: "all" | "alive" | "dead" | "blocked" = "all",
  filterStatus: "all" | "verified" | "has_claims" | "independent" | "suspect" = "all"
): { source: Source; index: number; attachedClaims: Claim[]; categories: ThematicCategory[] }[] {
  const claimsByUrl = new Map<string, Claim[]>();
  for (const c of claims) {
    if (c.source_url) {
      const list = claimsByUrl.get(c.source_url) ?? [];
      list.push(c);
      claimsByUrl.set(c.source_url, list);
    }
  }

  const query = searchQuery.trim().toLowerCase();

  return sources
    .map((source, index) => {
      const attachedClaims = claimsByUrl.get(source.url) ?? [];
      const categories = getSourceCategories(source, attachedClaims);
      return { source, index, attachedClaims, categories };
    })
    .filter(({ source, attachedClaims, categories }) => {
      // Category filter
      if (selectedCategory !== "all" && selectedCategory !== "discarded") {
        if (!categories.includes(selectedCategory)) return false;
      }

      // Liveness filter
      if (filterLiveness === "alive" && source.liveness !== "alive") return false;
      if (filterLiveness === "dead" && source.liveness !== "dead") return false;
      if (filterLiveness === "blocked" && source.liveness !== "blocked") return false;

      // Status filter
      if (filterStatus === "verified" && !source.human_verified) return false;
      if (filterStatus === "has_claims" && attachedClaims.length === 0) return false;
      if (filterStatus === "independent" && !source.is_independent) return false;
      if (filterStatus === "suspect" && source.identity_status !== "suspect") return false;

      // Keyword Search
      if (query) {
        const textToSearch = `${source.title || ""} ${source.snippet || ""} ${source.publisher || ""} ${source.url || ""} ${attachedClaims.map(c => c.text).join(" ")}`.toLowerCase();
        if (!textToSearch.includes(query)) return false;
      }

      return true;
    });
}
