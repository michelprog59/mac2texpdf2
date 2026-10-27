#!/usr/bin/env python3
import sys, os, subprocess, tempfile, shutil, re, platform, datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext


# --- macOS: LOCATING EXECUTABLES ---

def find_exe(name, extra_paths=()):
    """Look in PATH first, then in the usual macOS locations."""
    found = shutil.which(name)
    if found:
        return found
    for p in extra_paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


MAXIMA_CANDIDATES = [
    "/opt/homebrew/bin/maxima",
    "/usr/local/bin/maxima",
    "/Applications/Maxima.app/Contents/Resources/maxima.sh",
    "/Applications/Maxima.app/Contents/Resources/bin/maxima",
]
PDFLATEX_CANDIDATES = [
    "/Library/TeX/texbin/pdflatex",
    "/opt/homebrew/bin/pdflatex",
    "/usr/local/bin/pdflatex",
]
GNUPLOT_CANDIDATES = [
    "/opt/homebrew/bin/gnuplot",
    "/usr/local/bin/gnuplot",
    "/Applications/Maxima.app/Contents/Resources/bin/gnuplot",
]


def build_env():
    """PATH for subprocesses (Maxima needs gnuplot, found in Homebrew dirs)."""
    env = os.environ.copy()
    extra = ["/opt/homebrew/bin", "/usr/local/bin", "/Library/TeX/texbin",
             "/Applications/Maxima.app/Contents/Resources",
             "/Applications/Maxima.app/Contents/Resources/bin"]
    env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


def run_cmd(args, env, cwd=None, timeout=120):
    """Run a command, return (returncode, stdout, stderr); never raises."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, errors='replace',
                           env=env, cwd=cwd, stdin=subprocess.DEVNULL, timeout=timeout)
        return r.returncode, r.stdout or '', r.stderr or ''
    except subprocess.TimeoutExpired:
        return -1, '', f'TIMEOUT after {timeout} s'
    except Exception as e:
        return -2, '', f'{type(e).__name__}: {e}'


# --- PROCESSING LOGIC ---

SHOW_RESULT_FOR_DOLLAR = True   # True: also show the result of commands ending with $
NL_MARK = "@@NL@@"              # carries line breaks through the CMD: line


def read_commands_from_text(text):
    """Split the text into commands ending with ; or $ (outside strings and comments).
    Returns a list of (command, silent). silent = ended with $."""
    cmds = []
    buf = []
    n = len(text)
    i = 0

    def buffer_empty():
        return not ''.join(buf).strip()

    def finish(terminator):
        cmd = ''.join(buf)
        buf.clear()
        lines = [ln.rstrip() for ln in cmd.split('\n') if ln.strip()]
        if lines:
            lines[0] = lines[0].lstrip()
            silent = (terminator == '$') and not SHOW_RESULT_FOR_DOLLAR
            cmds.append(('\n'.join(lines), silent))

    while i < n:
        c = text[i]

        # Comment lines (only at the start of a command): *, %%, #
        if (i == 0 or text[i - 1] == '\n') and buffer_empty():
            end = text.find('\n', i)
            end = n if end == -1 else end
            if text[i:end].lstrip().startswith(('*', '%%', '#')):
                i = end
                continue

        if c == '"':                                   # string literal
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == '\\' else 1
            buf.append(text[i:j + 1])
            i = j + 1
        elif text.startswith('/*', i):                 # comment (can be nested)
            depth, j = 1, i + 2
            while j < n and depth:
                if text.startswith('/*', j):
                    depth += 1
                    j += 2
                elif text.startswith('*/', j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            buf.append(' ')
            i = j
        elif c in ';$':
            finish(c)
            i += 1
        else:
            buf.append(c)
            i += 1

    finish(';')          # last command without terminator
    return cmds


def replace_percent(cmd):
    """Replace the lone % (previous result) by _prev, outside strings."""
    parts = re.split(r'("(?:[^"\\]|\\.)*")', cmd)
    for k in range(0, len(parts), 2):      # even indices = outside strings
        parts[k] = re.sub(r'%(?![A-Za-z0-9_%])', '_prev', parts[k])
    return ''.join(parts)


# wxMaxima graphics commands -> standard Maxima equivalents
WX_TO_STD = {
    'wxdraw2d': 'draw2d', 'wxdraw3d': 'draw3d', 'wxdraw': 'draw',
    'wxplot2d': 'plot2d', 'wxplot3d': 'plot3d',
    'wximplicit_plot': 'implicit_plot', 'wxcontour_plot': 'contour_plot',
}
RE_WX = re.compile(r'\b(' + '|'.join(WX_TO_STD) + r')\s*\(')
RE_DRAW = re.compile(r'\b(draw2d|draw3d|draw)\s*\(')
RE_PLOT = re.compile(r'\b(plot2d|plot3d|implicit_plot|contour_plot)\s*\(')
# Commands whose output is kept but whose returned value is hidden
RE_PRINT = re.compile(r'^\s*(print|printf|disp|display|ldisp|grind|for|while|unless)\b\s*\(?')


def normalize_wx(cmd):
    """wxdraw2d( -> draw2d(, wxplot2d( -> plot2d(, etc. (outside strings)."""
    parts = re.split(r'("(?:[^"\\]|\\.)*")', cmd)
    for k in range(0, len(parts), 2):
        parts[k] = RE_WX.sub(lambda m: WX_TO_STD[m.group(1)] + '(', parts[k])
    return ''.join(parts)


def generate_maxima_script(cmds, tex_path, tmpdir):
    esc_path = os.path.abspath(tex_path).replace('\\', '/')
    script = [
        'errcatch(texput(matrix, ["pmatrix"]));',
        'display2d: false;',
        'errcatch(load("draw"));',
        'errcatch(load("implicit_plot"));',
        '_prev : false;',
        f'with_stdout("{esc_path}",'
    ]

    for i, (cmd_orig, silent) in enumerate(cmds, 1):
        cmd_esc = (cmd_orig.replace('\\', '\\\\').replace('"', '\\"')
                   .replace('\n', NL_MARK))
        cmd = replace_percent(normalize_wx(cmd_orig))
        img_name = f"plot_{i}.png"
        img_path = os.path.join(tmpdir, img_name).replace('\\', '/')
        img_base = img_path[:-4]
        script.append(f'  print("---BLOCK---"), print("ID: {i}"), print("CMD: {cmd_esc}"),')

        if RE_DRAW.search(cmd):
            gfx_cmd = RE_DRAW.sub(
                lambda m: f'{m.group(1)}(terminal=png, file_name="{img_base}", ',
                cmd, count=1)
            script.append(f'  errcatch({gfx_cmd}), print("GFX: {img_name}"),')
        elif RE_PLOT.search(cmd):
            gfx_cmd = re.sub(r'\)\s*$', f', [png_file, "{img_path}"])', cmd)
            script.append(f'  errcatch({gfx_cmd}), print("GFX: {img_name}"),')
        else:
            hide = silent or bool(RE_PRINT.match(cmd))
            script.append(f'  val : errcatch({cmd}),')
            if hide:
                script.append('  if val = [] then print("RES: MATH_ERR") '
                              'else (_prev : val[1]),')
            else:
                script.append('  if val = [] then print("RES: MATH_ERR") '
                              'else (_prev : val[1], print("RES:"), tex(_prev, true)),')

    script[-1] = script[-1].rstrip(',')
    script.append('); quit();')
    return '\n'.join(script)


HEADER = r"""\documentclass[FONTSIZE]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amsfonts,amssymb,mathtools}
\usepackage{graphicx}
\usepackage[left=1.5cm, right=1.5cm, top=1.5cm, bottom=2cm]{geometry}
\usepackage[english]{babel}
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage[useregional]{datetime2}
\usepackage{listings}
\usepackage{xcolor}

% Style for commands (with automatic line wrapping)
\lstdefinestyle{commandstyle}{
basicstyle=\ttfamily\small,
breaklines=true,
breakatwhitespace=false,
columns=flexible,
keepspaces=true,
showstringspaces=false,
frame=none,
xleftmargin=0pt,
xrightmargin=0pt
}

% Allow line breaks inside math formulas
\allowdisplaybreaks

\pagestyle{fancy}
\lhead{} \chead{} \rhead{}
\cfoot{ }
\rfoot{page \thepage}
\lfoot{Generated on \DTMnow}
\renewcommand{\headrulewidth}{0.0pt}
\renewcommand{\footrulewidth}{0.5pt}
\title{Maxima Results (Yamwi)}
\author{Automatically generated}
\begin{document}
\noindent\fbox{\begin{minipage}{\textwidth}\centering\LARGE\scshape Maxima LaTeX-PDF Generation\end{minipage}}
"""


def split_top_level(content):
    """Split a TeX list at top-level commas only.
    Ignores '\\,' (thin space) and commas inside braces, parentheses or inner brackets."""
    parts, current, depth = [], [], 0
    for idx, ch in enumerate(content):
        if ch in '[({':
            depth += 1
        elif ch in '])}':
            depth -= 1
        if ch == ',' and depth == 1 and (idx == 0 or content[idx - 1] != '\\'):
            current.append(ch)
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append(''.join(current))
    return parts


def add_result(body, res_lines):
    """Append the LaTeX block of a result (accumulated lines) to body."""
    m = re.search(r'\\begin\{verbatim\}(.*?)\\end\{verbatim\}',
                  '\n'.join(res_lines), re.DOTALL)
    if m:
        body.append(r"\textcolor{red!70!black}{\textbf{Result:}}")
        body.append(r"\begin{lstlisting}[style=commandstyle]")
        body.extend(ln.strip().rstrip(';') for ln in m.group(1).strip().split('\n'))
        body.append(r"\end{lstlisting}")
        body.append(r"\medskip")
        return

    full_res = ' '.join(res_lines)
    body.append(r"\textcolor{red!70!black}{\textbf{Result:}}")

    if len(full_res) > 120 and full_res.startswith('$$') and full_res.endswith('$$'):
        content = full_res[2:-2].strip()

        if '\\left[' in content and '\\right]' in content:
            content = content.replace('\\left', '').replace('\\right', '')

            elements = split_top_level(content)
            lines = [''.join(elements[k:k + 10]).strip()
                     for k in range(0, len(elements), 10)]
            if lines:
                lines[-1] = lines[-1].rstrip(',').strip()

            if len(lines) > 1:
                body.append(r"\begin{flushleft}")
                body.append("$\\displaystyle \\begin{aligned}")
                for ln in lines:
                    body.append(f"&{ln} \\\\")
                body[-1] = body[-1][:-3]
                body.append("\\end{aligned}$")
                body.append(r"\end{flushleft}")
                return

        body.append(r"\begin{flushleft}")
        body.append(f"$\\displaystyle {content}$")
        body.append(r"\end{flushleft}")
    else:
        body.append(r"\begin{flushleft}")
        body.append("$\\displaystyle " + full_res.strip('$') + "$")
        body.append(r"\end{flushleft}")


def finalize_tex(tmp_tex, font_size, img_width):
    if not os.path.exists(tmp_tex):
        return False
    with open(tmp_tex, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    header = HEADER.replace("FONTSIZE", font_size)
    body = []
    in_res = False
    in_cmd = False
    res_lines = []
    out_lines = []

    def flush_output():
        if out_lines:
            body.append(r"\textcolor{green!40!black}{\textbf{Output:}}")
            body.append(r"\begin{lstlisting}[style=commandstyle]")
            body.extend(out_lines)
            body.append(r"\end{lstlisting}")
            body.append(r"\medskip")
            out_lines.clear()

    for line in lines:
        l = line.strip()
        if l.startswith("ID:"):
            body.append(f"\\subsection*{{Computation {l.split(':')[-1].strip()}}}")
        elif l.startswith("CMD:"):
            c = l[len("CMD:"):].strip()
            body.append(r"\textcolor{blue}{\textbf{Command:}}")
            body.append(r"\begin{lstlisting}[style=commandstyle]")
            body.extend(c.split(NL_MARK))
            body.append(r"\end{lstlisting}")
            body.append(r"\medskip")
            in_cmd = True
            in_res = False
            out_lines.clear()
        elif l.startswith("RES:"):
            flush_output()
            in_cmd = False
            in_res = True
            res_lines = []
        elif l.startswith("GFX:"):
            flush_output()
            in_cmd = False
            img = l[len("GFX:"):].strip()
            body.append(f"\\begin{{center}}\\includegraphics[width={img_width}\\textwidth]{{{img}}}\\end{{center}}")
        elif l.startswith("---BLOCK---"):
            flush_output()
            if in_res and res_lines:
                add_result(body, res_lines)
            in_res = False
            in_cmd = False
            res_lines = []
        elif in_res and l:
            res_lines.append(l)
        elif in_cmd and l:
            out_lines.append(l)

    flush_output()
    if in_res and res_lines:
        add_result(body, res_lines)

    with open(tmp_tex, 'w', encoding='utf-8') as f:
        f.write(header + "\n".join(body) + "\n" + r"\end{document}")
    return True


# --- GRAPHICAL INTERFACE ---

class YamwiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Maxima to LaTeX and PDF Editor - v3.1 (debug)")
        self.root.geometry("600x780")
        self.pdf_generated_path = None
        self.tmp_dir = None
        self.log_text = "No run yet."
        self.log_win = None
        self.log_widget = None

        tk.Label(root, text="Enter or paste your Maxima commands:",
                 font=("Arial", 10, "bold")).pack(pady=5)
        self.txt_input = scrolledtext.ScrolledText(root, width=70, height=18, font=("Courier", 11))
        self.txt_input.pack(padx=10, pady=5)

        for seq in ("<Control-a>", "<Control-A>", "<Command-a>", "<Command-A>"):
            try:
                self.txt_input.bind(seq, self.select_all)
            except tk.TclError:
                pass

        self.txt_input.insert(tk.END, "expand((a+b)^4);\nsolve(x^2 - 5*x + 6 = 0, x);\n"
                                      "draw2d(color=blue, explicit(sin(x), x, 0, 10));")

        opt_frame = tk.LabelFrame(root, text=" Rendering options ", padx=10, pady=10)
        opt_frame.pack(pady=10, fill=tk.X, padx=10)

        tk.Label(opt_frame, text="Font size:").grid(row=0, column=0)
        self.font_size = tk.StringVar(value="10pt")
        tk.OptionMenu(opt_frame, self.font_size, "10pt", "11pt", "12pt").grid(row=0, column=1, padx=10)

        tk.Label(opt_frame, text="Image width (0.1-1.0):").grid(row=0, column=2)
        self.img_scale = tk.DoubleVar(value=0.5)
        tk.Scale(opt_frame, from_=0.1, to=1.0, resolution=0.1, orient=tk.HORIZONTAL,
                 variable=self.img_scale).grid(row=0, column=3)

        self.btn_gen = tk.Button(root, text="GENERATE PDF", command=self.process,
                                 bg="lightblue", font=("Arial", 10, "bold"))
        self.btn_gen.pack(pady=10, ipady=5, fill=tk.X, padx=50)

        action_frame = tk.Frame(root)
        action_frame.pack(pady=5)
        self.btn_import = tk.Button(action_frame, text="Import .mac",
                                    command=self.import_mac, bg="#fff2b3")
        self.btn_import.pack(side=tk.LEFT, padx=5)
        self.btn_view = tk.Button(action_frame, text="View PDF",
                                  command=self.view_pdf, state=tk.DISABLED)
        self.btn_view.pack(side=tk.LEFT, padx=5)
        self.btn_save = tk.Button(action_frame, text="Export folder (TeX + Images + PDF)...",
                                  command=self.save_all, state=tk.DISABLED, bg="#d1ffcf")
        self.btn_save.pack(side=tk.LEFT, padx=5)

        diag_frame = tk.Frame(root)
        diag_frame.pack(pady=5)
        tk.Button(diag_frame, text="Show log", command=self.show_log).pack(side=tk.LEFT, padx=5)
        tk.Button(diag_frame, text="Diagnostics", command=self.run_diagnostics).pack(side=tk.LEFT, padx=5)

        tk.Button(root, text="Quit", command=root.quit, bg="orange").pack(pady=15)

    # ---- log window ----
    def show_log(self):
        if self.log_win is not None and self.log_win.winfo_exists():
            self.log_win.lift()
            self._fill_log()
            return
        win = tk.Toplevel(self.root)
        win.title("Log / Diagnostics")
        win.geometry("820x600")
        self.log_win = win
        self.log_widget = scrolledtext.ScrolledText(win, font=("Courier", 10), wrap=tk.NONE)
        self.log_widget.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        bar = tk.Frame(win)
        bar.pack(pady=5)
        tk.Button(bar, text="Copy all", command=self.copy_log).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="Save log...", command=self.save_log).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="Close", command=win.destroy).pack(side=tk.LEFT, padx=5)
        self._fill_log()

    def _fill_log(self):
        self.log_widget.config(state=tk.NORMAL)
        self.log_widget.delete("1.0", tk.END)
        self.log_widget.insert("1.0", self.log_text)
        self.log_widget.see("1.0")

    def copy_log(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.log_text)
        messagebox.showinfo("Log", "Log copied to the clipboard.")

    def save_log(self):
        path = filedialog.asksaveasfilename(title="Save log", initialfile="mac2texpdf_log.txt",
                                            defaultextension=".txt")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.log_text)

    def set_log(self, text, show=False):
        self.log_text = text
        if show or (self.log_win is not None and self.log_win.winfo_exists()):
            self.show_log()

    # ---- environment report ----
    def environment_report(self, env):
        out = []
        out.append(f"Date: {datetime.datetime.now().isoformat(timespec='seconds')}")
        out.append(f"macOS: {platform.mac_ver()[0]}  machine: {platform.machine()}")
        out.append(f"Python: {sys.version.split()[0]}  Tk: {self.root.tk.call('info', 'patchlevel')}")
        out.append(f"PATH used:\n  " + env['PATH'].replace(os.pathsep, '\n  '))
        for name, cands in (('maxima', MAXIMA_CANDIDATES), ('pdflatex', PDFLATEX_CANDIDATES),
                            ('gnuplot', GNUPLOT_CANDIDATES)):
            exe = find_exe(name, cands)
            out.append(f"\n{name}: {exe}")
            if exe:
                args = [exe, '--version'] if name != 'pdflatex' else [exe, '--version']
                rc, so, se = run_cmd(args, env, timeout=60)
                first = (so + se).strip().splitlines()[:2]
                out.append(f"  --version (rc={rc}): " + ' | '.join(first))
        return '\n'.join(out)

    def run_diagnostics(self):
        env = build_env()
        self.set_log("=== DIAGNOSTICS ===\n" + self.environment_report(env), show=True)

    def select_all(self, event=None):
        self.txt_input.tag_add("sel", "1.0", "end-1c")
        self.txt_input.mark_set("insert", "end-1c")
        self.txt_input.see("insert")
        return "break"

    def import_mac(self):
        path = filedialog.askopenfilename(
            title="Import a Maxima file",
            filetypes=[("Maxima files", "*.mac *.wxm *.txt"), ("All files", "*.*")])
        if not path:
            return
        content = None
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                with open(path, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                messagebox.showerror("Error", f"Unable to read file: {e}")
                return
        if content is None:
            messagebox.showerror("Error", "File encoding not recognized.")
            return
        self.txt_input.delete("1.0", tk.END)
        self.txt_input.insert("1.0", content.replace('\r\n', '\n'))

    def process(self):
        raw_text = self.txt_input.get("1.0", tk.END)
        cmds = read_commands_from_text(raw_text)

        if not cmds:
            messagebox.showerror("Error", "The text area is empty.")
            return

        env = build_env()
        log = ["=== ENVIRONMENT ===", self.environment_report(env), ""]

        maxima_exe = find_exe('maxima', MAXIMA_CANDIDATES)
        pdflatex_exe = find_exe('pdflatex', PDFLATEX_CANDIDATES)
        if not maxima_exe:
            self.set_log('\n'.join(log) + "\nERROR: Maxima not found.", show=True)
            messagebox.showerror("Error", "Maxima not found (brew install maxima, or Maxima.app).")
            return
        if not pdflatex_exe:
            self.set_log('\n'.join(log) + "\nERROR: pdflatex not found.", show=True)
            messagebox.showerror("Error", "pdflatex not found (install MacTeX or BasicTeX).")
            return

        self.tmp_dir = tempfile.mkdtemp()
        tex_path = os.path.join(self.tmp_dir, "out.tex")
        drv_path = os.path.join(self.tmp_dir, "drv.mac")
        log.append(f"Temp dir: {self.tmp_dir}")

        try:
            script = generate_maxima_script(cmds, tex_path, self.tmp_dir)
            with open(drv_path, 'w', encoding='utf-8') as f:
                f.write(script)
            log += ["", "=== MAXIMA SCRIPT (drv.mac) ===", script]

            rc, so, se = run_cmd([maxima_exe, '--very-quiet', '-b', drv_path], env,
                                 cwd=self.tmp_dir, timeout=180)
            log += ["", f"=== MAXIMA (rc={rc}) ===", "--- stdout ---", so,
                    "--- stderr ---", se,
                    f"out.tex created by Maxima: {os.path.exists(tex_path)}"]

            if finalize_tex(tex_path, self.font_size.get(), self.img_scale.get()):
                rc2, so2, se2 = run_cmd([pdflatex_exe, '-interaction=nonstopmode', 'out.tex'],
                                        env, cwd=self.tmp_dir, timeout=180)
                log += ["", f"=== PDFLATEX (rc={rc2}) ===",
                        "--- stdout (last 3000 chars) ---", so2[-3000:],
                        "--- stderr ---", se2]
                pdf_path = os.path.join(self.tmp_dir, "out.pdf")
                if os.path.exists(pdf_path):
                    self.pdf_generated_path = pdf_path
                    self.btn_view.config(state=tk.NORMAL)
                    self.btn_save.config(state=tk.NORMAL)
                    self.set_log('\n'.join(log))
                    messagebox.showinfo("Success", "Processing completed successfully.\n"
                                                   "(Use 'Show log' for details.)")
                else:
                    self.set_log('\n'.join(log), show=True)
                    messagebox.showerror("Error", "LaTeX compilation error. See the log window.")
            else:
                self.set_log('\n'.join(log), show=True)
                messagebox.showerror("Error", "Maxima could not process the commands. "
                                              "See the log window.")
        except Exception as e:
            log.append(f"\nEXCEPTION: {type(e).__name__}: {e}")
            self.set_log('\n'.join(log), show=True)
            messagebox.showerror("Error", str(e))

    def view_pdf(self):
        if self.pdf_generated_path:
            if sys.platform == "win32":
                os.startfile(self.pdf_generated_path)
            elif sys.platform == "darwin":
                subprocess.run(['open', self.pdf_generated_path])
            else:
                subprocess.run(['xdg-open', self.pdf_generated_path])

    def save_all(self):
        if not self.pdf_generated_path or not self.tmp_dir:
            return

        full_dest_path = filedialog.asksaveasfilename(
            title="Choose the export folder name",
            initialfile="export_session")

        if full_dest_path:
            export_dir = full_dest_path + "_folder"
            try:
                if not os.path.exists(export_dir):
                    os.makedirs(export_dir)

                base_name = os.path.basename(full_dest_path)
                shutil.copy2(self.pdf_generated_path, os.path.join(export_dir, base_name + ".pdf"))
                shutil.copy2(os.path.join(self.tmp_dir, "out.tex"),
                             os.path.join(export_dir, base_name + ".tex"))

                count_img = 0
                for file in os.listdir(self.tmp_dir):
                    if file.endswith(".png"):
                        shutil.copy2(os.path.join(self.tmp_dir, file), os.path.join(export_dir, file))
                        count_img += 1

                messagebox.showinfo("Export",
                                    f"Folder created: {export_dir}\nFiles: PDF, TeX and {count_img} image(s).")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = YamwiApp(root)
    root.mainloop()
