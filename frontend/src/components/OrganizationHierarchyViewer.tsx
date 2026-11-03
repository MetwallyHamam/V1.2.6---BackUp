import {
  AccountTree,
  Add,
  CenterFocusStrong,
  Close,
  Delete,
  Edit,
  Expand,
  Groups,
  ManageSearch,
  UnfoldLess,
  UnfoldMore,
  ZoomIn,
  ZoomOut,
} from "@mui/icons-material";
import {
  Avatar,
  Box,
  Button,
  ButtonGroup,
  Chip,
  Dialog,
  DialogContent,
  IconButton,
  InputAdornment,
  Paper,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { PointerEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";

export type OrganizationHierarchyNode = {
  id: number;
  parent_id: number | null;
  name: string;
  node_type: string;
  title?: string | null;
  image_url?: string | null;
  notes?: string | null;
  is_active?: boolean;
};

type Props = {
  nodes: OrganizationHierarchyNode[];
  loading?: boolean;
  emptyText?: string;
  configure?: boolean;
  onAdd?: (parent?: OrganizationHierarchyNode) => void;
  onEdit?: (node: OrganizationHierarchyNode) => void;
  onDelete?: (node: OrganizationHierarchyNode) => void;
  notice?: ReactNode;
};

const clamp = (value: number) => Math.max(0.45, Math.min(1.35, value));

export function OrganizationHierarchyViewer({
  nodes,
  loading,
  emptyText = "No hierarchy nodes yet.",
  configure,
  onAdd,
  onEdit,
  onDelete,
  notice,
}: Props) {
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("sm"));
  const [view, setView] = useState<"CHART" | "OUTLINE">(mobile ? "OUTLINE" : "CHART");
  const [search, setSearch] = useState("");
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());
  const [zoom, setZoom] = useState(1);
  const [fullScreen, setFullScreen] = useState(false);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const drag = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
  const children = useMemo(() => {
    const result = new Map<number | null, OrganizationHierarchyNode[]>();
    const ids = new Set(nodes.map((node) => node.id));
    for (const node of nodes) {
      const parent = node.parent_id && ids.has(node.parent_id) ? node.parent_id : null;
      result.set(parent, [...(result.get(parent) ?? []), node]);
    }
    return result;
  }, [nodes]);
  const roots = children.get(null) ?? [];
  const matches = useMemo(() => {
    const term = search.trim().toLowerCase();
    return new Set(
      term
        ? nodes.filter((node) => `${node.name} ${node.title ?? ""} ${node.node_type} ${node.notes ?? ""}`.toLowerCase().includes(term)).map((node) => node.id)
        : [],
    );
  }, [nodes, search]);
  useEffect(() => {
    if (!matches.size) return;
    setCollapsed((current) => {
      const next = new Set(current);
      for (const match of matches) {
        let parent = nodes.find((node) => node.id === match)?.parent_id;
        while (parent) {
          next.delete(parent);
          parent = nodes.find((node) => node.id === parent)?.parent_id;
        }
      }
      return next;
    });
    const timer = window.setTimeout(() => {
      const match = canvasRef.current?.querySelector<HTMLElement>(`[data-org-node="${[...matches][0]}"]`);
      match?.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
    }, 50);
    return () => window.clearTimeout(timer);
  }, [matches, nodes]);
  useEffect(() => {
    if (mobile) setView("OUTLINE");
  }, [mobile]);

  const descendants = (nodeId: number): number =>
    (children.get(nodeId) ?? []).reduce((total, child) => total + 1 + descendants(child.id), 0);
  const toggle = (id: number) =>
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const collapseAll = () => setCollapsed(new Set(nodes.filter((node) => children.has(node.id)).map((node) => node.id)));
  const fit = () => {
    setZoom(clamp((canvasRef.current?.clientWidth ?? 900) / Math.max(700, roots.length * 300)));
    if (canvasRef.current) {
      canvasRef.current.scrollLeft = 0;
      canvasRef.current.scrollTop = 0;
    }
  };
  const pointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (view !== "CHART" || !canvasRef.current || (event.target as HTMLElement).closest("button,a,input")) return;
    drag.current = { x: event.clientX, y: event.clientY, left: canvasRef.current.scrollLeft, top: canvasRef.current.scrollTop };
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const pointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!drag.current || !canvasRef.current) return;
    canvasRef.current.scrollLeft = drag.current.left - (event.clientX - drag.current.x);
    canvasRef.current.scrollTop = drag.current.top - (event.clientY - drag.current.y);
  };

  const card = (node: OrganizationHierarchyNode, compact = false) => {
    const kids = children.get(node.id) ?? [];
    const team = node.node_type === "TEAM";
    return (
      <Paper
        data-org-node={node.id}
        variant="outlined"
        sx={(palette) => ({
          width: compact ? "100%" : 224,
          p: compact ? 1.25 : 1.5,
          borderRadius: 3,
          borderColor: matches.has(node.id) ? "warning.main" : alpha(palette.palette.primary.main, .2),
          borderWidth: matches.has(node.id) ? 2 : 1,
          bgcolor: node.is_active === false ? "action.disabledBackground" : "background.paper",
          boxShadow: matches.has(node.id) ? `0 0 0 4px ${alpha(palette.palette.warning.main, .15)}` : undefined,
        })}
      >
        <Stack direction="row" gap={1} alignItems="center">
          <Avatar src={node.image_url || undefined} sx={{ bgcolor: team ? "secondary.main" : "primary.main", width: 44, height: 44 }}>
            {team ? <Groups /> : node.name[0]}
          </Avatar>
          <Box minWidth={0} flex={1} textAlign="start">
            <Typography fontWeight={900} noWrap>{node.name}</Typography>
            <Typography variant="caption" color="primary.main" fontWeight={800} display="block" noWrap>{node.title || node.node_type.replaceAll("_", " ")}</Typography>
            <Typography variant="caption" color="text.secondary">{kids.length} direct · {descendants(node.id)} total</Typography>
          </Box>
          {!!kids.length && <IconButton size="small" aria-label={collapsed.has(node.id) ? `Expand ${node.name}` : `Collapse ${node.name}`} onClick={() => toggle(node.id)}>{collapsed.has(node.id) ? <UnfoldMore fontSize="small" /> : <UnfoldLess fontSize="small" />}</IconButton>}
        </Stack>
        {node.notes && !compact && <Typography variant="caption" color="text.secondary" display="block" mt={1}>{node.notes}</Typography>}
        {configure && <Stack direction="row" justifyContent="flex-end" mt={.5}>
          <IconButton size="small" aria-label={`Add child to ${node.name}`} onClick={() => onAdd?.(node)}><Add fontSize="small" /></IconButton>
          <IconButton size="small" aria-label={`Edit ${node.name}`} onClick={() => onEdit?.(node)}><Edit fontSize="small" /></IconButton>
          <IconButton size="small" color="error" aria-label={`Delete ${node.name}`} onClick={() => onDelete?.(node)}><Delete fontSize="small" /></IconButton>
        </Stack>}
      </Paper>
    );
  };

  const branch = (node: OrganizationHierarchyNode): ReactNode => {
    const kids = children.get(node.id) ?? [];
    const shown = !collapsed.has(node.id) ? kids : [];
    return <Stack key={node.id} alignItems="center" sx={{ minWidth: 244 }}>
      {card(node)}
      {!!shown.length && <><Box sx={{ width: 2, height: 22, bgcolor: "divider" }} /><Box sx={{ display: "flex", gap: 2, pt: 2.5, position: "relative", "&::before": { content: '""', position: "absolute", top: 0, left: shown.length === 1 ? "50%" : `${100 / (shown.length * 2)}%`, right: shown.length === 1 ? "50%" : `${100 / (shown.length * 2)}%`, borderTop: shown.length === 1 ? 0 : "2px solid", borderColor: "divider" } }}>{shown.map((child) => <Box key={child.id} sx={{ position: "relative", "&::before": { content: '""', position: "absolute", top: -20, left: "50%", height: 20, borderLeft: "2px solid", borderColor: "divider" } }}>{branch(child)}</Box>)}</Box></>}
    </Stack>;
  };
  const outline = (node: OrganizationHierarchyNode, depth = 0): ReactNode => {
    const kids = children.get(node.id) ?? [];
    return <Box key={node.id} sx={{ ml: Math.min(depth, 6) * 1.5, mb: 1 }}>
      {card(node, true)}
      {!collapsed.has(node.id) && kids.map((child) => outline(child, depth + 1))}
    </Box>;
  };
  const viewer = (
    <Stack spacing={1.5} height="100%">
      <Stack direction={{ xs: "column", md: "row" }} gap={1} alignItems={{ md: "center" }}>
        {notice && <Box flex={1}>{notice}</Box>}
        <TextField size="small" placeholder="Find a person, position, role, or team" value={search} onChange={(event) => setSearch(event.target.value)} sx={{ minWidth: { md: 340 } }} slotProps={{ input: { startAdornment: <InputAdornment position="start"><ManageSearch /></InputAdornment> } }} />
        <ToggleButtonGroup size="small" exclusive value={view} onChange={(_, value) => value && setView(value)}>
          <ToggleButton value="CHART"><AccountTree fontSize="small" /> Chart</ToggleButton>
          <ToggleButton value="OUTLINE"><Groups fontSize="small" /> Outline</ToggleButton>
        </ToggleButtonGroup>
        <ButtonGroup size="small">
          <Tooltip title="Expand all"><IconButton onClick={() => setCollapsed(new Set())}><UnfoldMore /></IconButton></Tooltip>
          <Tooltip title="Collapse all"><IconButton onClick={collapseAll}><UnfoldLess /></IconButton></Tooltip>
          {view === "CHART" && <>
            <Tooltip title="Zoom out"><IconButton onClick={() => setZoom((value) => clamp(value - .1))}><ZoomOut /></IconButton></Tooltip>
            <Chip label={`${Math.round(zoom * 100)}%`} sx={{ borderRadius: 0 }} />
            <Tooltip title="Zoom in"><IconButton onClick={() => setZoom((value) => clamp(value + .1))}><ZoomIn /></IconButton></Tooltip>
            <Tooltip title="Fit to screen"><IconButton onClick={fit}><CenterFocusStrong /></IconButton></Tooltip>
          </>}
          {!fullScreen && <Tooltip title="Full screen"><IconButton onClick={() => setFullScreen(true)}><Expand /></IconButton></Tooltip>}
        </ButtonGroup>
      </Stack>
      <Box ref={canvasRef} onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={() => { drag.current = null; }} sx={{ overflow: "auto", minHeight: view === "CHART" ? 520 : 260, flex: 1, p: 2, bgcolor: (palette) => alpha(palette.palette.primary.main, .025), borderRadius: 3, cursor: drag.current ? "grabbing" : view === "CHART" ? "grab" : "default", touchAction: "pan-x pan-y" }}>
        {view === "CHART" ? <Box sx={{ width: "max-content", minWidth: "100%", transform: `scale(${zoom})`, transformOrigin: "top center", pb: `${Math.max(0, (1 - zoom) * 300)}px` }}><Stack direction="row" gap={3} justifyContent="center" alignItems="flex-start">{roots.map((root) => branch(root))}</Stack></Box> : <Box maxWidth={900} mx="auto">{roots.map((root) => outline(root))}</Box>}
        {!roots.length && <Stack alignItems="center" py={7} color="text.secondary"><AccountTree sx={{ fontSize: 52 }} /><Typography fontWeight={800}>{loading ? "Loading…" : emptyText}</Typography>{configure && <Button startIcon={<Add />} onClick={() => onAdd?.()}>Add root node</Button>}</Stack>}
      </Box>
    </Stack>
  );
  return <>
    {viewer}
    <Dialog open={fullScreen} onClose={() => setFullScreen(false)} fullScreen>
      <Stack direction="row" alignItems="center" px={2} py={1}><Typography variant="h6" fontWeight={900} flex={1}>Organization Hierarchy</Typography><IconButton aria-label="Close full screen" onClick={() => setFullScreen(false)}><Close /></IconButton></Stack>
      <DialogContent sx={{ p: 2, overflow: "hidden" }}>{viewer}</DialogContent>
    </Dialog>
  </>;
}
