from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_TAB_ALIGNMENT


OUTPUT = r"D:\Metwally\Developing tools\Support Operations Systems\Web CRM & Ticketing System\V1.2.6 - BackUp\Support_Hub_AI_Cloud_Server_Deployment_Guide.docx"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=110, start=130, bottom=110, end=130):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color="D9D9D9", size="6"):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:color"), color)


def repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def keep_with_next(paragraph):
    paragraph.paragraph_format.keep_with_next = True


def add_field(run, instruction):
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])


def add_code(doc, text):
    p = doc.add_paragraph(style="Command")
    p.paragraph_format.keep_together = True
    lines = text.strip("\n").splitlines()
    for i, line in enumerate(lines):
        r = p.add_run(line)
        if i < len(lines) - 1:
            r.add_break()
    return p


def add_bullets(doc, items):
    for item in items:
        doc.add_paragraph(item, style="List Bullet")


def add_number(doc, lead, body):
    p = doc.add_paragraph(style="List Number")
    r = p.add_run(lead)
    r.bold = True
    p.add_run(body)
    return p


def add_table(doc, headers, rows, widths):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    header = table.rows[0]
    repeat_table_header(header)
    for i, text in enumerate(headers):
        cell = header.cells[i]
        cell.width = widths[i]
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_shading(cell, "1F4E78")
        set_cell_margins(cell)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(text)
        r.bold = True
        r.font.color.rgb = RGBColor(255, 255, 255)
    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(values):
            cells[i].width = widths[i]
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cells[i])
            if row_index % 2:
                set_cell_shading(cells[i], "F2F6FA")
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.add_run(str(value))
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


doc = Document()
section = doc.sections[0]
section.top_margin = Inches(0.72)
section.bottom_margin = Inches(0.72)
section.left_margin = Inches(0.82)
section.right_margin = Inches(0.82)

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Aptos"
normal.font.size = Pt(10.2)
normal.font.color.rgb = RGBColor(35, 35, 35)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.08

title = styles["Title"]
title.font.name = "Aptos Display"
title.font.size = Pt(25)
title.font.bold = True
title.font.color.rgb = RGBColor(0, 0, 0)
title.paragraph_format.space_after = Pt(10)

for style_name, size, before, after in (
    ("Heading 1", 16, 16, 7),
    ("Heading 2", 12.5, 12, 5),
    ("Heading 3", 11, 9, 3),
):
    st = styles[style_name]
    st.font.name = "Aptos Display"
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.paragraph_format.space_before = Pt(before)
    st.paragraph_format.space_after = Pt(after)
    st.paragraph_format.keep_with_next = True

command = styles.add_style("Command", WD_STYLE_TYPE.PARAGRAPH)
command.font.name = "Consolas"
command.font.size = Pt(8.5)
command.font.color.rgb = RGBColor(25, 25, 25)
command.paragraph_format.left_indent = Inches(0.28)
command.paragraph_format.right_indent = Inches(0.1)
command.paragraph_format.space_before = Pt(3)
command.paragraph_format.space_after = Pt(7)
command.paragraph_format.line_spacing = 1.0

for list_style in (styles["List Bullet"], styles["List Number"]):
    list_style.font.name = "Aptos"
    list_style.font.size = Pt(10.2)
    list_style.paragraph_format.space_after = Pt(3)

# Header and footer
header = section.header
hp = header.paragraphs[0]
hp.text = "MILLENSYS SUPPORT HUB   |   OPERATIONS GUIDE"
hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
hp.runs[0].font.name = "Aptos"
hp.runs[0].font.size = Pt(8)
hp.runs[0].font.color.rgb = RGBColor(90, 90, 90)

footer = section.footer
fp = footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fr = fp.add_run("Support Hub AI Cloud Server Deployment Guide   |   Page ")
fr.font.size = Pt(8)
fr.font.color.rgb = RGBColor(100, 100, 100)
page_run = fp.add_run()
add_field(page_run, "PAGE")

# Cover
p = doc.add_paragraph(style="Title")
p.add_run("Support Hub AI Cloud Server Deployment Guide")
sub = doc.add_paragraph()
sub.paragraph_format.space_after = Pt(18)
r = sub.add_run("Windows Server  |  IIS HTTPS  |  Ollama  |  qwen2.5 7b")
r.font.size = Pt(13)
r.font.color.rgb = RGBColor(60, 60, 60)

intro = doc.add_paragraph()
intro.add_run("Purpose. ").bold = True
intro.add_run(
    "This guide prepares a new Windows cloud server to run the Millensys Support Hub and its local AI model securely. "
    "The public website uses HTTPS through IIS, while the Local AI gateway and Ollama remain private on the server loopback interface."
)

decision = doc.add_paragraph()
decision.add_run("Required design. ").bold = True
decision.add_run(
    "Expose only the Support Hub website on TCP 443. Do not publish Local AI port 8090 or Ollama port 11434 to the internet. "
    "The current Local AI endpoints do not provide independent client authentication."
)

add_table(
    doc,
    ["Document item", "Value"],
    [
        ("Audience", "Cloud and Windows Server administrators"),
        ("Target platform", "Windows Server with IIS and optional NVIDIA GPU"),
        ("Public URL", "https://support.example.com/SupportHub  Replace with the real DNS name"),
        ("AI model", "qwen2.5:7b through Ollama"),
        ("Deployment model", "Support Hub, Local AI, and Ollama on the same server"),
        ("Version", "1.0  September 2026"),
    ],
    [Inches(1.65), Inches(5.0)],
)

doc.add_heading("Deployment outcome", level=1)
doc.add_paragraph(
    "After completing this procedure, users reach Support Hub through a trusted HTTPS URL. IIS runs the application backend, "
    "the backend calls Local AI at 127.0.0.1:8090, and Local AI calls Ollama at 127.0.0.1:11434. Both AI processes start automatically after a reboot."
)

doc.add_heading("Production architecture", level=1)
arch = [
    ("1", "Internet users", "HTTPS", "TCP 443", "IIS public endpoint"),
    ("2", "IIS", "Internal application routing", "Dynamic local port", "Support Hub backend"),
    ("3", "Support Hub backend", "HTTP loopback", "127.0.0.1:8090", "Local AI gateway"),
    ("4", "Local AI gateway", "HTTP loopback", "127.0.0.1:11434", "Ollama"),
    ("5", "Ollama", "Local disk and CPU or GPU", "No public port", "qwen2.5:7b"),
]
add_table(doc, ["Stage", "Source", "Connection", "Endpoint", "Destination"], arch,
          [Inches(0.48), Inches(1.33), Inches(1.55), Inches(1.48), Inches(1.75)])

doc.add_heading("Before you begin", level=1)
add_bullets(doc, [
    "Reserve a static public IP and a production DNS name.",
    "Obtain administrator access to Windows Server, IIS, DNS, the cloud firewall, and the SQL Server network.",
    "Use at least 16 GB RAM; 32 GB is preferred for reliable application and model operation.",
    "Reserve at least 30 GB of free disk space for software, model files, logs, and temporary data.",
    "For responsive inference, use a supported NVIDIA GPU with at least 8 GB VRAM and a current driver.",
    "Prepare new production secrets. Do not reuse credentials previously shared in messages or screenshots.",
])

doc.add_page_break()
doc.add_heading("1 Prepare Windows and the cloud firewall", level=1)
add_number(doc, "Patch the server. ", "Install current Windows security updates and restart before installing application components.")
add_number(doc, "Create storage directories. ", "Use a stable data volume when available.")
add_code(doc, r'''New-Item -ItemType Directory -Path "E:\SupportHub\Release" -Force
New-Item -ItemType Directory -Path "E:\SupportHub\Storage\attachments" -Force
New-Item -ItemType Directory -Path "E:\SupportHub\Storage\backups" -Force
New-Item -ItemType Directory -Path "E:\SupportHub\OllamaModels" -Force''')
add_number(doc, "Configure inbound access. ", "Allow TCP 443 publicly. Allow TCP 80 only when needed for certificate issuance or redirection. Restrict RDP to the administrator IP or VPN.")
add_number(doc, "Block internal service ports. ", "Do not create cloud firewall or Windows Firewall rules for TCP 8090 or 11434.")

add_table(doc, ["Port", "Exposure", "Purpose", "Required control"], [
    ("443", "Public", "Support Hub HTTPS", "Trusted certificate and IIS binding"),
    ("80", "Optional public", "Certificate validation and redirect", "Redirect all application traffic to HTTPS"),
    ("3389", "Restricted", "Administration", "Allow only VPN or named administrator IPs"),
    ("8090", "Loopback only", "Local AI gateway", "No inbound firewall rule"),
    ("11434", "Loopback only", "Ollama API", "No inbound firewall rule"),
    ("1433", "Private only", "SQL Server", "Private network and explicit source restriction"),
], [Inches(0.65), Inches(1.25), Inches(2.2), Inches(2.55)])

doc.add_heading("2 Configure DNS and HTTPS", level=1)
add_number(doc, "Create the DNS record. ", "Point the production hostname to the server public IP.")
add_code(doc, "support.example.com    A    CLOUD_PUBLIC_IP")
add_number(doc, "Install IIS. ", "Install the IIS role and the components required by the Support Hub deployment package.")
add_number(doc, "Install the certificate. ", "Use a certificate trusted by client devices and containing the production hostname.")
add_number(doc, "Create the HTTPS binding. ", "Bind the certificate to the Support Hub IIS site on TCP 443 and select the correct hostname.")
add_number(doc, "Enforce HTTPS. ", "Redirect HTTP requests to HTTPS and verify that no application login or API call remains on HTTP.")

doc.add_heading("3 Install Python", level=1)
doc.add_paragraph("Install 64-bit Python 3.12 for all users. Enable the Python launcher and PATH options during installation. Open a new Administrator PowerShell window and verify:")
add_code(doc, "py -3.12 --version")
doc.add_paragraph("Do not copy a Python virtual environment from another server. Virtual environments contain machine-specific executable paths and native packages.")

doc.add_heading("4 Install and configure Ollama", level=1)
doc.add_paragraph("Install Ollama for Windows using the official installer or the official standalone Windows package when integrating it as a service. Verify the installation in a new terminal:")
add_code(doc, "ollama --version")
doc.add_paragraph("If the installer did not add Ollama to PATH, verify the default per-user location:")
add_code(doc, '& "$env:LOCALAPPDATA\\Programs\\Ollama\\ollama.exe" --version')

doc.add_heading("Set production environment variables", level=2)
doc.add_paragraph("Set these values at machine scope so the service account receives them. The settings keep the API on loopback, move model data to the application data volume, and disable optional cloud-model features.")
add_code(doc, r'''[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", "E:\SupportHub\OllamaModels", "Machine")
[Environment]::SetEnvironmentVariable("OLLAMA_NO_CLOUD", "1", "Machine")
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "127.0.0.1:11434", "Machine")''')
doc.add_paragraph("Restart Ollama or restart Windows after changing machine environment variables.")

doc.add_heading("Download the model", level=2)
add_code(doc, "ollama serve")
doc.add_paragraph("Keep the server process running. In a second Administrator PowerShell window:")
add_code(doc, "ollama pull qwen2.5:7b\nollama list")

doc.add_heading("Test direct inference", level=2)
add_code(doc, r'''$body = @{
    model  = "qwen2.5:7b"
    prompt = "Return exactly: AI model is ready"
    stream = $false
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
    -Uri "http://127.0.0.1:11434/api/generate" `
    -ContentType "application/json" `
    -Body $body''')
doc.add_paragraph("Confirm processing placement after a request:")
add_code(doc, "ollama ps")
doc.add_paragraph("The PROCESSOR column indicates whether the model is using CPU, GPU, or a mixture of both.")

doc.add_page_break()
doc.add_heading("5 Deploy the Local AI gateway", level=1)
doc.add_paragraph("Copy the release Local AI directory to the following location without carrying over an existing virtual environment:")
add_code(doc, r'''E:\SupportHub\Release\local-ai''')
doc.add_paragraph("Stop any old Local AI process before replacing or rebuilding the environment. Then run:")
add_code(doc, r'''cd "E:\SupportHub\Release\local-ai"

if (Test-Path ".\venv") {
    Remove-Item -LiteralPath ".\venv" -Recurse -Force
}

py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt''')

doc.add_heading("Configure Local AI", level=2)
doc.add_paragraph("Create or verify E:\\SupportHub\\Release\\local-ai\\.env:")
add_code(doc, "OLLAMA_BASE_URL=http://127.0.0.1:11434\nOLLAMA_MODEL=qwen2.5:7b\nOLLAMA_TIMEOUT_SECONDS=120")
doc.add_paragraph("For the recommended same-server design, run the gateway on loopback:")
add_code(doc, r'''.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8090''')
doc.add_paragraph("Test the gateway:")
add_code(doc, 'Invoke-RestMethod "http://127.0.0.1:8090/health"')
doc.add_paragraph("Expected status: ok, with service name Support Hub Local AI.")

doc.add_heading("6 Configure the Support Hub backend", level=1)
doc.add_paragraph("Use the real production hostname in the deployed backend web.config. Keep Local AI on loopback when it runs on the same Windows server:")
add_code(doc, r'''<environmentVariable name="APP_ENV" value="production" />
<environmentVariable name="FRONTEND_ORIGIN"
  value="https://support.example.com" />
<environmentVariable name="FRONTEND_BASE_URL"
  value="https://support.example.com/SupportHub" />
<environmentVariable name="TRUSTED_HOSTS"
  value="support.example.com,localhost,127.0.0.1" />
<environmentVariable name="LOCAL_AI_ENABLED" value="true" />
<environmentVariable name="LOCAL_AI_BASE_URL"
  value="http://127.0.0.1:8090" />
<environmentVariable name="LOCAL_AI_TIMEOUT_SECONDS" value="120" />''')
doc.add_paragraph("Also replace every deployment secret and credential with a newly issued production value. Store the authoritative secret values in an approved password vault and restrict access to web.config.")
doc.add_paragraph("After deploying the configuration, restart the site or application pool. A full IIS restart can be used during a controlled maintenance window:")
add_code(doc, "iisreset")

doc.add_heading("7 Configure automatic startup", level=1)
doc.add_paragraph("Interactive terminal windows are suitable only for installation tests. In production, run Ollama and Local AI under a dedicated Windows service account with automatic startup and restart-on-failure behavior.")
add_table(doc, ["Service", "Command", "Account requirements"], [
    ("Ollama", "ollama serve", "Read and write OllamaModels; GPU access; machine environment variables"),
    ("Local AI", "E:\\SupportHub\\Release\\local-ai\\run.bat", "Read release directory; execute Python; connect to 127.0.0.1:11434"),
], [Inches(1.05), Inches(2.55), Inches(3.05)])
doc.add_paragraph("Configure service dependencies or delayed startup so Ollama becomes available before Local AI begins accepting application requests. Configure both services to restart after failure and direct stdout and stderr to a monitored log location.")

doc.add_page_break()
doc.add_heading("8 Validate the complete deployment", level=1)
doc.add_heading("Local service tests", level=2)
add_code(doc, r'''Test-NetConnection 127.0.0.1 -Port 11434
Test-NetConnection 127.0.0.1 -Port 8090

Invoke-RestMethod "http://127.0.0.1:11434/api/tags"
Invoke-RestMethod "http://127.0.0.1:8090/health"

ollama list
ollama ps''')

doc.add_heading("Public HTTPS test", level=2)
add_code(doc, 'Invoke-WebRequest "https://support.example.com/SupportHub"')
doc.add_paragraph("Verify the certificate chain, hostname, expiration date, HTTP status, and redirect behavior from a computer outside the cloud network.")

doc.add_heading("Application test", level=2)
add_number(doc, "Sign in through HTTPS. ", "Confirm that the browser shows a valid certificate and does not load mixed HTTP content.")
add_number(doc, "Create a controlled test ticket. ", "Use non-sensitive sample data.")
add_number(doc, "Run AI intake. ", "Confirm that a title and structured description are returned.")
add_number(doc, "Run AI resolution. ", "Confirm that the request completes within the configured timeout.")
add_number(doc, "Review logs. ", "Confirm there are no 502 responses, connection errors, model-not-found errors, or repeated process restarts.")

doc.add_heading("Acceptance checklist", level=1)
checks = [
    ("☐", "DNS", "Production hostname resolves to the cloud server public IP"),
    ("☐", "HTTPS", "Trusted certificate is bound to IIS on TCP 443"),
    ("☐", "Firewall", "Only required public ports are open; 8090 and 11434 are private"),
    ("☐", "Ollama", "API responds on 127.0.0.1:11434"),
    ("☐", "Model", "qwen2.5:7b appears in ollama list and answers a test prompt"),
    ("☐", "Local AI", "Health endpoint responds on 127.0.0.1:8090"),
    ("☐", "Backend", "LOCAL_AI_BASE_URL points to http://127.0.0.1:8090"),
    ("☐", "Application", "AI intake and resolution work from the HTTPS user interface"),
    ("☐", "Startup", "Both AI processes return after a controlled server restart"),
    ("☐", "Security", "Previously exposed credentials have been rotated"),
    ("☐", "Monitoring", "Service failures and disk usage generate alerts"),
    ("☐", "Backup", "Configuration and application data are included in backup procedures"),
]
add_table(doc, ["Done", "Area", "Acceptance criterion"], checks,
          [Inches(0.6), Inches(1.25), Inches(4.85)])

doc.add_heading("Troubleshooting", level=1)
add_table(doc, ["Symptom", "Likely cause", "Corrective action"], [
    ("8090 health test fails", "Local AI is stopped, bound incorrectly, or its virtual environment is broken", "Start run.bat; check the process; rebuild venv locally with Python 3.12"),
    ("11434 tags test fails", "Ollama is not installed or not running", "Start ollama serve under the production service account"),
    ("Model not found", "qwen2.5:7b was not pulled for the active Ollama model location", "Verify OLLAMA_MODELS and run ollama pull qwen2.5:7b"),
    ("Access denied deleting venv", "Python has loaded native files from the environment", "Stop the Local AI process or service before removing venv"),
    ("Backend returns 502", "Local AI cannot reach Ollama or inference exceeded the timeout", "Test both local endpoints; inspect logs; verify model and hardware capacity"),
    ("Works interactively but fails after reboot", "Processes are tied to a user session or use different environment variables", "Run both as services under one documented service account"),
    ("Inference is very slow", "Model is using CPU or insufficient GPU memory", "Run ollama ps; validate drivers and GPU capacity"),
    ("HTTPS hostname rejected", "TRUSTED_HOSTS, DNS, or certificate name is incorrect", "Align all three values with the production hostname"),
], [Inches(1.65), Inches(2.15), Inches(2.9)])

doc.add_heading("Separate AI server variation", level=1)
doc.add_paragraph(
    "If Ollama and Local AI must run on a different cloud server, connect the servers through a private virtual network or VPN. "
    "Do not publish the current Local AI API directly to the internet. Bind port 8090 only to the private interface, restrict its firewall source to the Support Hub server, and add API authentication or mutual TLS before production use."
)
doc.add_paragraph("Only in that architecture should the Support Hub setting use the private AI-server address, for example:")
add_code(doc, '<environmentVariable name="LOCAL_AI_BASE_URL" value="http://10.20.0.15:8090" />')
doc.add_paragraph("Keep Ollama on 127.0.0.1:11434 on the AI server. The public Support Hub HTTPS URL does not need to expose either AI port.")

doc.add_heading("Operational maintenance", level=1)
add_bullets(doc, [
    "Review Windows, IIS, Support Hub, Local AI, and Ollama logs after deployments and service restarts.",
    "Monitor disk usage for model files, attachments, backups, and logs.",
    "Test AI intake and resolution after every model, Ollama, Python, or application upgrade.",
    "Apply upgrades in a maintenance window and retain a rollback copy of application configuration.",
    "Back up configuration and business data. The model can normally be downloaded again, but verify recovery time requirements.",
    "Review service-account permissions periodically and remove interactive logon where operationally practical.",
])

doc.add_heading("Official references", level=1)
refs = [
    ("Ollama Windows installation", "https://docs.ollama.com/windows"),
    ("Ollama configuration and networking", "https://docs.ollama.com/faq"),
    ("Ollama API introduction", "https://docs.ollama.com/api/introduction"),
    ("Microsoft IIS reverse proxy with ARR", "https://learn.microsoft.com/en-us/iis/extensions/url-rewrite-module/reverse-proxy-with-url-rewrite-v2-and-application-request-routing"),
]
for label, url in refs:
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(label + ": ").bold = True
    p.add_run(url)

doc.core_properties.title = "Support Hub AI Cloud Server Deployment Guide"
doc.core_properties.subject = "Production deployment of Support Hub Local AI and Ollama on Windows Server"
doc.core_properties.author = "Millensys"
doc.core_properties.keywords = "Support Hub, Ollama, qwen2.5, Windows Server, IIS, HTTPS, Local AI"
doc.core_properties.comments = "Production operations guide"

doc.save(OUTPUT)
print(OUTPUT)
