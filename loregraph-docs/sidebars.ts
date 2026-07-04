import type { SidebarsConfig } from "@docusaurus/plugin-content-docs";

// Ordered for a newcomer: orient → vocabulary → how it fits → how data moves →
// what you can tune → what's uncertain.
const sidebars: SidebarsConfig = {
  docs: [
    "intro",
    {
      type: "category",
      label: "Getting Started",
      collapsed: false,
      items: ["onboarding/start-here", "onboarding/knowledge-map"]
    },
    {
      type: "category",
      label: "Business Terms",
      items: [
        "business-terms/glossary",
        "business-terms/reconciliation",
        "business-terms/settlement",
        "business-terms/allocation",
        "business-terms/fill",
        "business-terms/trade-break",
        "business-terms/counterparty",
        "business-terms/course",
        "business-terms/semester-plan",
        "business-terms/plan-warning",
        "business-terms/plan",
        "business-terms/requirement",
        "business-terms/student",
        "business-terms/requirement-progress",
        "business-terms/audit-report",
        "business-terms/plan-compare-result",
        "business-terms/advisor-tool-call",
        "business-terms/advisor",
        "business-terms/agent-trace",
        "business-terms/critic-violation",
        "business-terms/session-state",
        "business-terms/msg",
        "business-terms/props",
        "business-terms/tabs-props"
      ]
    },
    {
      type: "category",
      label: "Architecture",
      items: ["architecture/overview", "architecture/service-map", "architecture/concept-map"]
    },
    {
      type: "category",
      label: "Flows",
      items: ["flows/inferred-flows", "flows/kafka-flows"]
    },
    {
      type: "category",
      label: "Configuration",
      items: [
        "configuration/overview",
        "configuration/config-keys",
        "configuration/feature-flags",
        "configuration/environment-variables"
      ]
    },
    {
      type: "category",
      label: "Operations",
      items: ["operations/open-questions", "operations/docs-drift-report"]
    }
  ]
};

export default sidebars;
