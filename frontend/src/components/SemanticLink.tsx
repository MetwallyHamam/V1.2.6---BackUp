import { Link as MuiLink, LinkProps as MuiLinkProps } from '@mui/material'
import { Link as RouterLink, type LinkProps as RouterLinkProps } from 'react-router-dom'
type SemanticLinkProps = Omit<MuiLinkProps, 'href'> & Pick<RouterLinkProps, 'to' | 'state'>
export function SemanticLink({ to, state, children, ...props }: SemanticLinkProps) { return <MuiLink component={RouterLink} to={to} state={state} {...props}>{children}</MuiLink> }
