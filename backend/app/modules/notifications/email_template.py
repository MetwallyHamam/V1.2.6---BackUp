import html
import re
from urllib.parse import urlsplit

URL_PATTERN = re.compile(r"https?://[^\s<>]+")


def frontend_url(base_url: str, deep_link: str | None = None) -> str:
    """Join a public SPA base and application link without losing or duplicating /SupportHub."""
    base = base_url.strip().rstrip("/")
    if not deep_link:
        return base
    path = "/" + deep_link.strip().lstrip("/")
    base_path = urlsplit(base).path.rstrip("/")
    if base_path and (path == base_path or path.startswith(f"{base_path}/")):
        path = path[len(base_path):] or "/"
    return f"{base}{path}"


def branded_email_html(subject: str, body: str, action_url: str | None = None) -> str:
    """Render a safe, responsive, Outlook-friendly Support Hub email."""
    detected_url = action_url or next(iter(URL_PATTERN.findall(body)), None)
    escaped_body = html.escape(body)
    for url in URL_PATTERN.findall(body):
        escaped = html.escape(url)
        escaped_body = escaped_body.replace(escaped, f'<a href="{escaped}" style="color:#0e7490;text-decoration:underline">{escaped}</a>')
    paragraphs = "".join(
        f'<p style="margin:0 0 16px;font-size:15px;line-height:1.72;color:#334155">{part.replace(chr(10), "<br>")}</p>'
        for part in escaped_body.split("\n\n")
        if part.strip()
    )
    safe_subject = html.escape(subject)
    subject_lower = subject.lower()
    if "contract" in subject_lower and ("expir" in subject_lower or "renew" in subject_lower):
        badge, accent, tint = "CONTRACT EXPIRATION", "#f97316", "#fff7ed"
    elif "sla" in subject_lower or "escalat" in subject_lower or "warning" in subject_lower:
        badge, accent, tint = "ACTION REQUIRED", "#f97316", "#fff7ed"
    elif "password" in subject_lower or "security" in subject_lower:
        badge, accent, tint = "SECURITY NOTICE", "#7c3aed", "#f5f3ff"
    elif "mention" in subject_lower:
        badge, accent, tint = "YOU WERE MENTIONED", "#0891b2", "#ecfeff"
    else:
        badge, accent, tint = "SUPPORT UPDATE", "#0f766e", "#f0fdfa"
    action = ""
    if detected_url:
        safe_url = html.escape(detected_url, quote=True)
        action = f"""
        <tr><td style="padding:2px 40px 30px">
          <table role="presentation" cellspacing="0" cellpadding="0"><tr><td bgcolor="#0e7490" style="border-radius:10px;box-shadow:0 5px 14px rgba(14,116,144,.22)">
            <a href="{safe_url}" style="display:inline-block;border:1px solid #0e7490;border-radius:10px;background:#0e7490;color:#ffffff!important;text-decoration:none;font-size:15px;font-weight:700;line-height:20px;padding:13px 24px">Open in Support Hub&nbsp;&nbsp;→</a>
          </td></tr></table>
          <p style="margin:16px 0 0;font-size:12px;line-height:1.55;color:#64748b">Button not working? Copy and paste this secure link:<br><a href="{safe_url}" style="color:#0e7490;text-decoration:underline;word-break:break-all">{safe_url}</a></p>
        </td></tr>"""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light"><title>{safe_subject}</title><style>:root{{color-scheme:light only}} body,table,td,a{{-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%}} table,td{{mso-table-lspace:0;mso-table-rspace:0}} table{{border-collapse:collapse!important}} .supporthub-header,.supporthub-header *{{color:#ffffff!important;-webkit-text-fill-color:#ffffff!important}} @media only screen and (max-width:620px){{.email-shell{{padding:12px!important}} .email-card{{border-radius:12px!important}} .email-pad{{padding-left:22px!important;padding-right:22px!important}} .email-title{{font-size:24px!important}}}}</style></head>
<body style="margin:0;padding:0;background:#edf2f7;font-family:'Segoe UI',Arial,sans-serif;color:#0f172a">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent">{safe_subject} — Open Millensys Support Hub for details.</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" bgcolor="#edf2f7"><tr><td class="email-shell" align="center" style="padding:36px 14px">
<table role="presentation" class="email-card" width="100%" cellspacing="0" cellpadding="0" style="max-width:680px;background:#ffffff;border:1px solid #dbe4ee;border-radius:18px;overflow:hidden;box-shadow:0 14px 40px rgba(15,23,42,.10)">
<tr><td class="supporthub-header email-pad" bgcolor="#071d49" style="padding:28px 40px;background-color:#071d49;background-image:linear-gradient(125deg,#071d49 0%,#0b3b68 55%,#0e7490 100%);color:#ffffff!important">
  <table role="presentation" width="100%"><tr><td valign="middle"><table role="presentation"><tr><td width="42" height="42" align="center" bgcolor="#ffffff" style="width:42px;height:42px;border-radius:11px;color:#071d49!important;-webkit-text-fill-color:#071d49!important;font-size:18px;font-weight:900">M</td><td style="padding-left:12px"><div style="font-size:15px;font-weight:800;letter-spacing:.3px;color:#ffffff!important">MILLENSYS</div><div style="font-size:11px;letter-spacing:1.6px;color:#bae6fd!important">SUPPORT HUB</div></td></tr></table></td><td align="right" valign="middle"><span style="display:inline-block;border:1px solid rgba(255,255,255,.34);border-radius:999px;padding:6px 10px;font-size:10px;font-weight:700;letter-spacing:1px;color:#ffffff!important">NOTIFICATION</span></td></tr></table>
  <div style="height:24px;line-height:24px">&nbsp;</div><span style="display:inline-block;background:{tint};color:{accent}!important;-webkit-text-fill-color:{accent}!important;border-radius:999px;padding:6px 10px;font-size:10px;font-weight:800;letter-spacing:1.2px">{badge}</span>
  <h1 class="email-title" style="margin:12px 0 0;font-size:28px;line-height:1.28;font-weight:750;color:#ffffff!important;-webkit-text-fill-color:#ffffff!important">{safe_subject}</h1>
</td></tr>
<tr><td height="5" bgcolor="{accent}" style="height:5px;font-size:0;line-height:0">&nbsp;</td></tr>
<tr><td class="email-pad" style="padding:34px 40px 12px"><div style="padding:20px 22px 4px;background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid {accent};border-radius:12px">{paragraphs}</div></td></tr>
{action}
<tr><td class="email-pad" style="padding:0 40px 30px"><table role="presentation" width="100%" style="border-top:1px solid #e2e8f0"><tr><td style="padding-top:20px;font-size:12px;line-height:1.6;color:#64748b"><strong style="color:#334155">Security reminder</strong><br>Millensys will never ask for your password by email. Only open links from a trusted Millensys Support Hub notification.</td></tr></table></td></tr>
<tr><td class="email-pad" bgcolor="#071d49" style="padding:24px 40px;background:#071d49;color:#cbd5e1;text-align:center;font-size:12px;line-height:1.7"><strong style="color:#ffffff;letter-spacing:.8px">MILLENSYS</strong>&nbsp;&nbsp;•&nbsp;&nbsp;Technology for a Healthier Globe<br>Automated notification from the Support Hub Platform<br><span style="color:#7dd3fc">© 2026 Millensys.</span></td></tr>
</table><p style="margin:16px 0 0;font-size:11px;color:#94a3b8">Please do not reply to this automated message.</p></td></tr></table></body></html>"""
