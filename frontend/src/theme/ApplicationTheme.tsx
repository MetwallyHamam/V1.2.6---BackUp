import createCache from "@emotion/cache";
import { CacheProvider } from "@emotion/react";
import { CssBaseline, ThemeProvider, createTheme, alpha } from "@mui/material";
import { ReactNode, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { prefixer } from "stylis";
import rtlPlugin from "stylis-plugin-rtl";
import { useAuth } from "../auth/AuthContext";
import { SearchableSelectMenuList } from "../components/SearchableSelectMenuList";

const ltrCache = createCache({ key: "mui" });
const rtlCache = createCache({
  key: "muirtl",
  stylisPlugins: [prefixer, rtlPlugin],
});

const themePresets = {
  CLASSIC: {
    font: "Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#4f46e5",
      secondary: "#0891b2",
      page: "#f6f7fb",
      paper: "#ffffff",
      header: "#312e81",
      nav: "#fafaff",
      border: "rgba(49,46,129,.13)",
    },
    dark: {
      primary: "#818cf8",
      secondary: "#22d3ee",
      page: "#0b1020",
      paper: "#12182b",
      header: "#17144b",
      nav: "#10162a",
      border: "rgba(165,180,252,.20)",
    },
  },
  OCEAN: {
    font: "Manrope, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#0f766e",
      secondary: "#0284c7",
      page: "#f0fdfa",
      paper: "#ffffff",
      header: "#0f4c5c",
      nav: "#f5fffd",
      border: "rgba(15,118,110,.15)",
    },
    dark: {
      primary: "#2dd4bf",
      secondary: "#38bdf8",
      page: "#071a1d",
      paper: "#0d2529",
      header: "#082f3a",
      nav: "#0a2024",
      border: "rgba(94,234,212,.20)",
    },
  },
  FOREST: {
    font: "Manrope, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#047857",
      secondary: "#65a30d",
      page: "#f2f8f5",
      paper: "#ffffff",
      header: "#064e3b",
      nav: "#f7fcf9",
      border: "rgba(4,120,87,.15)",
    },
    dark: {
      primary: "#34d399",
      secondary: "#a3e635",
      page: "#081711",
      paper: "#10231b",
      header: "#06372b",
      nav: "#0d1d17",
      border: "rgba(110,231,183,.19)",
    },
  },
  SUNSET: {
    font: "Plus Jakarta Sans, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#e11d48",
      secondary: "#d97706",
      page: "#fff7ed",
      paper: "#fffdf9",
      header: "#9f1239",
      nav: "#fffaf4",
      border: "rgba(190,24,93,.14)",
    },
    dark: {
      primary: "#fb7185",
      secondary: "#fbbf24",
      page: "#21100e",
      paper: "#2b1715",
      header: "#6b102d",
      nav: "#251311",
      border: "rgba(253,164,175,.20)",
    },
  },
  PLUM: {
    font: "Plus Jakarta Sans, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#7c3aed",
      secondary: "#db2777",
      page: "#faf5ff",
      paper: "#fffaff",
      header: "#581c87",
      nav: "#fdf8ff",
      border: "rgba(126,34,206,.14)",
    },
    dark: {
      primary: "#a78bfa",
      secondary: "#f472b6",
      page: "#180d22",
      paper: "#24132f",
      header: "#3b125b",
      nav: "#20102b",
      border: "rgba(216,180,254,.20)",
    },
  },
  COBALT: {
    font: "Manrope, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#1d4ed8",
      secondary: "#0284c7",
      page: "#f5f8ff",
      paper: "#ffffff",
      header: "#1e3a8a",
      nav: "#f7f9ff",
      border: "rgba(29,78,216,.15)",
    },
    dark: {
      primary: "#60a5fa",
      secondary: "#38bdf8",
      page: "#091426",
      paper: "#101d33",
      header: "#102a5c",
      nav: "#0d192b",
      border: "rgba(96,165,250,.21)",
    },
  },
  MIDNIGHT: {
    font: "Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#0f172a",
      secondary: "#0891b2",
      page: "#f1f5f9",
      paper: "#ffffff",
      header: "#020617",
      nav: "#f8fafc",
      border: "rgba(15,23,42,.15)",
    },
    dark: {
      primary: "#22d3ee",
      secondary: "#818cf8",
      page: "#020617",
      paper: "#0f172a",
      header: "#020617",
      nav: "#0b1220",
      border: "rgba(34,211,238,.20)",
    },
  },
  TERRACOTTA: {
    font: "Plus Jakarta Sans, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#9a3412",
      secondary: "#ea580c",
      page: "#fff8f1",
      paper: "#fffdf9",
      header: "#7c2d12",
      nav: "#fffbf5",
      border: "rgba(154,52,18,.15)",
    },
    dark: {
      primary: "#fb923c",
      secondary: "#fbbf24",
      page: "#1c100b",
      paper: "#29170f",
      header: "#5c210f",
      nav: "#24140e",
      border: "rgba(251,146,60,.20)",
    },
  },
  GRAPHITE: {
    font: "Manrope, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#3f6212",
      secondary: "#65a30d",
      page: "#f7f7f5",
      paper: "#ffffff",
      header: "#27272a",
      nav: "#fafaf9",
      border: "rgba(63,98,18,.16)",
    },
    dark: {
      primary: "#a3e635",
      secondary: "#22c55e",
      page: "#101113",
      paper: "#1c1d20",
      header: "#18181b",
      nav: "#17181a",
      border: "rgba(163,230,53,.20)",
    },
  },
  NORDIC: {
    font: "Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#334155",
      secondary: "#2563eb",
      page: "#f8fafc",
      paper: "#ffffff",
      header: "#1e293b",
      nav: "#f8fafc",
      border: "rgba(51,65,85,.15)",
    },
    dark: {
      primary: "#93c5fd",
      secondary: "#67e8f9",
      page: "#0b1120",
      paper: "#151e2f",
      header: "#172033",
      nav: "#111827",
      border: "rgba(147,197,253,.20)",
    },
  },
  AURORA: {
    font: "Plus Jakarta Sans, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#6d28d9",
      secondary: "#0d9488",
      page: "#f5f3ff",
      paper: "#ffffff",
      header: "#312e81",
      nav: "#faf8ff",
      border: "rgba(109,40,217,.15)",
    },
    dark: {
      primary: "#a78bfa",
      secondary: "#2dd4bf",
      page: "#0c1021",
      paper: "#17172d",
      header: "#25164f",
      nav: "#121328",
      border: "rgba(167,139,250,.22)",
    },
  },
  SAKURA: {
    font: "Plus Jakarta Sans, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#be185d",
      secondary: "#7c3aed",
      page: "#fff5f8",
      paper: "#ffffff",
      header: "#831843",
      nav: "#fff9fb",
      border: "rgba(190,24,93,.14)",
    },
    dark: {
      primary: "#f472b6",
      secondary: "#c4b5fd",
      page: "#1d0d18",
      paper: "#2a1422",
      header: "#5b1238",
      nav: "#24101d",
      border: "rgba(244,114,182,.22)",
    },
  },
  NEON: {
    font: "Manrope, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#4338ca",
      secondary: "#059669",
      page: "#f4f7ff",
      paper: "#ffffff",
      header: "#1e1b4b",
      nav: "#f8faff",
      border: "rgba(67,56,202,.16)",
    },
    dark: {
      primary: "#22d3ee",
      secondary: "#a3e635",
      page: "#050816",
      paper: "#0d1326",
      header: "#11114a",
      nav: "#090e20",
      border: "rgba(34,211,238,.24)",
    },
  },
  MOCHA: {
    font: "Plus Jakarta Sans, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#8b4513",
      secondary: "#b45309",
      page: "#faf6f1",
      paper: "#fffdf9",
      header: "#57301f",
      nav: "#fcf8f3",
      border: "rgba(120,72,45,.17)",
    },
    dark: {
      primary: "#d6a477",
      secondary: "#f59e0b",
      page: "#17110e",
      paper: "#241a15",
      header: "#3f281d",
      nav: "#1e1612",
      border: "rgba(214,164,119,.22)",
    },
  },
  ARCTIC: {
    font: "Manrope, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#0369a1",
      secondary: "#0f766e",
      page: "#f0f9ff",
      paper: "#ffffff",
      header: "#0c4a6e",
      nav: "#f6fcff",
      border: "rgba(3,105,161,.14)",
    },
    dark: {
      primary: "#7dd3fc",
      secondary: "#5eead4",
      page: "#06141f",
      paper: "#0d2230",
      header: "#0b3954",
      nav: "#091b27",
      border: "rgba(125,211,252,.22)",
    },
  },
  OBSIDIAN_GOLD: {
    font: "Manrope, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#854d0e",
      secondary: "#52525b",
      page: "#fafaf9",
      paper: "#ffffff",
      header: "#27272a",
      nav: "#f8f7f4",
      border: "rgba(133,77,14,.17)",
    },
    dark: {
      primary: "#facc15",
      secondary: "#d4d4d8",
      page: "#09090b",
      paper: "#18181b",
      header: "#18130a",
      nav: "#111113",
      border: "rgba(250,204,21,.22)",
    },
  },
  MILLENSYS: {
    font: "Manrope, Inter, Segoe UI, Arial, sans-serif",
    light: {
      primary: "#13778F",
      secondary: "#3F82C4",
      page: "#F2F8FA",
      paper: "#FFFFFF",
      header: "#02303F",
      nav: "#F7FBFC",
      border: "rgba(19,119,143,.17)",
    },
    dark: {
      primary: "#96BDF4",
      secondary: "#52C1D2",
      page: "#06171D",
      paper: "#0C252D",
      header: "#02303F",
      nav: "#091F27",
      border: "rgba(150,189,244,.23)",
    },
  },
} as const;

export function ApplicationTheme({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { i18n } = useTranslation();
  const direction = i18n.resolvedLanguage === "ar" ? "rtl" : "ltr";
  const [prefersDark, setPrefersDark] = useState(
    () => window.matchMedia("(prefers-color-scheme: dark)").matches,
  );
  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const update = (event: MediaQueryListEvent) =>
      setPrefersDark(event.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  const mode =
    user?.theme_mode === "DARK" ||
    (user?.theme_mode === "SYSTEM" && prefersDark)
      ? "dark"
      : "light";
  const preset =
    themePresets[user?.theme_preset ?? "CLASSIC"] ?? themePresets.CLASSIC;
  const colors = preset[mode];
  const theme = useMemo(
    () =>
      createTheme({
        direction,
        palette: {
          mode,
          primary: { main: colors.primary },
          secondary: { main: colors.secondary },
          background: { default: colors.page, paper: colors.paper },
          divider: colors.border,
          text:
            mode === "dark"
              ? {
                  primary: "#f8fafc",
                  secondary: "#cbd5e1",
                  disabled: "#7c8ba1",
                }
              : {
                  primary: colors.header,
                  secondary: "#526175",
                  disabled: "#8995a7",
                },
          ...(mode === "dark"
            ? {
                action: {
                  hover: "rgba(105, 167, 255, 0.09)",
                  selected: "rgba(105, 167, 255, 0.16)",
                  focus: "rgba(105, 167, 255, 0.18)",
                  disabledBackground: "rgba(169, 184, 206, 0.12)",
                },
              }
            : {}),
        },
        shape: { borderRadius: 14 },
        typography: {
          fontFamily:
            direction === "rtl" ? "Tahoma, Arial, sans-serif" : preset.font,
          h4: { fontWeight: 750, letterSpacing: "-0.025em" },
          h6: { fontWeight: 700 },
        },
        components: {
          MuiCssBaseline: {
            styleOverrides: {
              ":root": { colorScheme: mode },
              "html, body, #root": { maxWidth: "100%", minWidth: 0 },
              body: {
                transition: "background-color 180ms ease, color 180ms ease",
                overflowX: "hidden",
              },
              img: { maxWidth: "100%", height: "auto" },
              "pre, code, a, p": { overflowWrap: "anywhere" },
              '.technical-text, [data-technical-text="true"]': {
                direction: "ltr",
                unicodeBidi: "isolate",
              },
              'input[type="email"], input[type="url"], input[type="tel"], input[name*="phone"], input[name*="timezone"], input[name*="code"], input[name*="number"], input[name*="server"], input[name*="database"], input[name*="ip_address"]':
                { direction: "ltr", unicodeBidi: "plaintext" },
              "::selection": {
                backgroundColor: alpha(
                  mode === "dark" ? "#69a7ff" : "#1769aa",
                  0.35,
                ),
              },
            },
          },
          MuiPaper: {
            styleOverrides: {
              root: {
                backgroundImage: "none",
                minWidth: 0,
                maxWidth: "100%",
                borderColor:
                  mode === "dark" ? "rgba(169, 184, 206, 0.2)" : undefined,
              },
            },
          },
          MuiAppBar: {
            styleOverrides: {
              root: {
                backgroundImage: `linear-gradient(110deg, ${colors.header}, ${colors.primary})`,
                color: "#fff",
              },
            },
          },
          MuiDrawer: {
            styleOverrides: {
              paper: {
                backgroundImage: "none",
                backgroundColor: colors.nav,
                borderColor: colors.border,
              },
            },
          },
          MuiTableCell: {
            styleOverrides: {
              root: {
                borderColor:
                  mode === "dark" ? "rgba(169, 184, 206, 0.16)" : undefined,
              },
              head: {
                backgroundColor: mode === "dark" ? "#152238" : undefined,
                fontWeight: 700,
              },
            },
          },
          MuiTable: {
            styleOverrides: {
              root: {
                display: "block",
                maxWidth: "100%",
                overflowX: "auto",
                WebkitOverflowScrolling: "touch",
              },
            },
          },
          MuiTableContainer: {
            styleOverrides: {
              root: {
                maxWidth: "100%",
                overflowX: "auto",
                WebkitOverflowScrolling: "touch",
              },
            },
          },
          MuiMenu: {
            styleOverrides: {
              paper: {
                border: `1px solid ${mode === "dark" ? "rgba(169, 184, 206, 0.2)" : "rgba(15, 23, 42, 0.08)"}`,
              },
            },
          },
          MuiButton: {
            defaultProps: { disableElevation: true },
            styleOverrides: {
              root: ({ theme }) => ({
                borderRadius: 10,
                textTransform: "none",
                fontWeight: 650,
                minHeight: 40,
                [theme.breakpoints.down("sm")]: { minHeight: 44 },
              }),
              containedInherit: {
                backgroundColor: mode === "dark" ? "#334155" : "#e2e8f0",
                color: mode === "dark" ? "#f8fafc" : "#0f172a",
                "&:hover": {
                  backgroundColor: mode === "dark" ? "#475569" : "#cbd5e1",
                },
                "&.Mui-disabled": {
                  backgroundColor:
                    mode === "dark" ? "rgba(71, 85, 105, .48)" : "#e5e7eb",
                  color:
                    mode === "dark" ? "rgba(248, 250, 252, .5)" : "#64748b",
                },
              },
            },
          },
          MuiIconButton: {
            styleOverrides: {
              root: ({ theme }) => ({
                [theme.breakpoints.down("sm")]: { minWidth: 44, minHeight: 44 },
              }),
            },
          },
          MuiTextField: { defaultProps: { variant: "outlined" } },
          MuiSelect: {
            defaultProps: {
              MenuProps: {
                slots: { list: SearchableSelectMenuList },
                disableEnforceFocus: true,
                disableAutoFocusItem: true,
                anchorOrigin: {
                  vertical: "bottom",
                  horizontal: direction === "rtl" ? "right" : "left",
                },
                transformOrigin: {
                  vertical: "top",
                  horizontal: direction === "rtl" ? "right" : "left",
                },
                slotProps: {
                  paper: {
                    sx: {
                      mt: 0.75,
                      maxHeight: "min(360px, calc(100vh - 24px))",
                    },
                  },
                },
              },
            },
          },
          MuiOutlinedInput: {
            styleOverrides: {
              root: ({ theme }) => ({
                borderRadius: 11,
                backgroundColor: alpha(theme.palette.background.paper, 0.72),
                transition: "box-shadow 160ms ease, border-color 160ms ease",
                "&.Mui-focused": {
                  boxShadow: `0 0 0 3px ${alpha(theme.palette.primary.main, 0.14)}`,
                },
              }),
            },
          },
          MuiDialog: {
            styleOverrides: {
              paper: ({ theme }) => ({
                borderRadius: 18,
                border:
                  mode === "dark"
                    ? "1px solid rgba(169, 184, 206, 0.2)"
                    : undefined,
                [theme.breakpoints.down("sm")]: {
                  margin: 8,
                  width: "calc(100% - 16px)",
                  maxHeight: "calc(100% - 16px)",
                  borderRadius: 12,
                },
              }),
              paperWidthMd: { maxWidth: 1400 },
            },
          },
          MuiDialogActions: {
            styleOverrides: {
              root: ({ theme }) => ({
                flexWrap: "wrap",
                gap: theme.spacing(0.5),
                [theme.breakpoints.down("sm")]: {
                  padding: theme.spacing(1.5),
                  "& > :not(style) ~ :not(style)": { marginInlineStart: 0 },
                  "& .MuiButton-root": { flex: "1 1 auto" },
                },
              }),
            },
          },
          MuiDialogTitle: {
            styleOverrides: {
              root: ({ theme }) => ({
                overflowWrap: "anywhere",
                [theme.breakpoints.down("sm")]: { padding: theme.spacing(2) },
              }),
            },
          },
          MuiDialogContent: {
            styleOverrides: {
              root: ({ theme }) => ({
                minWidth: 0,
                [theme.breakpoints.down("sm")]: {
                  paddingInline: theme.spacing(2),
                },
              }),
            },
          },
          MuiTabs: {
            styleOverrides: {
              root: { maxWidth: "100%" },
              flexContainer: { minWidth: 0 },
            },
          },
          MuiCard: {
            styleOverrides: {
              root: { borderRadius: 16, backgroundImage: "none" },
            },
          },
          MuiTooltip: {
            styleOverrides: {
              tooltip: {
                backgroundColor: mode === "dark" ? "#dbe7f7" : "#182235",
                color: mode === "dark" ? "#0b1220" : "#fff",
              },
            },
          },
        },
      }),
    [colors, direction, mode, preset.font],
  );
  return (
    <CacheProvider value={direction === "rtl" ? rtlCache : ltrCache}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </CacheProvider>
  );
}
