import { Box, type BoxProps } from "@mui/material";

export function TechnicalText(props: BoxProps) {
  return (
    <Box
      component="span"
      {...props}
      sx={{ direction: "ltr", unicodeBidi: "isolate", ...props.sx }}
    />
  );
}
