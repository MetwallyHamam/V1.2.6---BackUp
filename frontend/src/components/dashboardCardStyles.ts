/**
 * The dashboard treatment mirrors the actionable ticket cards in Support Assistant:
 * one status-coloured leading border, restrained surface gradient, and clear hover affordance.
 */
export const dashboardTicketCardSx = (accent: string, interactive = false) => ({
  position: "relative",
  overflow: "hidden",
  borderRadius: 3,
  border: "1px solid",
  borderColor: "divider",
  borderInlineStartWidth: 6,
  borderInlineStartColor: accent,
  background: (theme: { palette: { mode: string } }) =>
    theme.palette.mode === "dark"
      ? "linear-gradient(145deg, rgba(30,41,59,.98), rgba(15,23,42,.94))"
      : "linear-gradient(145deg, rgba(255,255,255,.98), rgba(248,250,252,.92))",
  boxShadow: `0 10px 28px rgba(15,23,42,.10), 0 0 22px -18px ${accent}`,
  transition: "transform .18s ease, box-shadow .18s ease, border-color .18s ease",
  ...(interactive
    ? {
        cursor: "pointer",
        "&:hover": {
          transform: "translateY(-3px)",
          borderColor: `${accent}66`,
          borderInlineStartColor: accent,
          boxShadow: `0 16px 38px rgba(15,23,42,.16), 0 0 26px -17px ${accent}`,
        },
        "&:focus-visible": {
          outline: `3px solid ${accent}55`,
          outlineOffset: 2,
        },
      }
    : {}),
});
