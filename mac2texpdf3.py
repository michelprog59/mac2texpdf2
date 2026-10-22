#!/usr/bin/env python3
import sys, os, subprocess, tempfile, shutil, re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext

# --- LOGIQUE DE TRAITEMENT ---

AFFICHER_RESULTAT_DOLLAR = True   # True : afficher aussi le résultat des commandes finissant par $
MARQUE_NL = "@@NL@@"              # transmet les retours à la ligne dans la ligne CMD:


def lire_commandes_depuis_texte(texte):
    """Découpe le texte en commandes terminées par ; ou $ (hors chaînes et commentaires).
    Retourne une liste de (commande, silencieux). silencieux = terminée par $."""
    cmds = []
    buf = []
    n = len(texte)
    i = 0

    def tampon_vide():
        return not ''.join(buf).strip()

    def terminer(terminateur):
        cmd = ''.join(buf)
        buf.clear()
        lignes = [ln.rstrip() for ln in cmd.split('\n') if ln.strip()]
        if lignes:
            lignes[0] = lignes[0].lstrip()
            silencieux = (terminateur == '$') and not AFFICHER_RESULTAT_DOLLAR
            cmds.append(('\n'.join(lignes), silencieux))

    while i < n:
        c = texte[i]

        # Lignes de commentaire (début de commande uniquement) : *, %%, #
        if (i == 0 or texte[i - 1] == '\n') and tampon_vide():
            fin = texte.find('\n', i)
            fin = n if fin == -1 else fin
            if texte[i:fin].lstrip().startswith(('*', '%%', '#')):
                i = fin
                continue

        if c == '"':                                   # chaîne de caractères
            j = i + 1
            while j < n and texte[j] != '"':
                j += 2 if texte[j] == '\\' else 1
            buf.append(texte[i:j + 1])
            i = j + 1
        elif texte.startswith('/*', i):                # commentaire (imbriquable)
            profondeur, j = 1, i + 2
            while j < n and profondeur:
                if texte.startswith('/*', j):
                    profondeur += 1
                    j += 2
                elif texte.startswith('*/', j):
                    profondeur -= 1
                    j += 2
                else:
                    j += 1
            buf.append(' ')
            i = j
        elif c in ';$':
            terminer(c)
            i += 1
        else:
            buf.append(c)
            i += 1

    terminer(';')          # dernière commande sans terminateur
    return cmds


def remplacer_pourcent(cmd):
    """Remplace le % seul (dernier résultat) par _prev, hors chaînes."""
    morceaux = re.split(r'("(?:[^"\\]|\\.)*")', cmd)
    for k in range(0, len(morceaux), 2):      # indices pairs = hors chaînes
        morceaux[k] = re.sub(r'%(?![A-Za-z0-9_%])', '_prev', morceaux[k])
    return ''.join(morceaux)


# Commandes graphiques wxMaxima -> équivalents Maxima standard
WX_VERS_STD = {
    'wxdraw2d': 'draw2d', 'wxdraw3d': 'draw3d', 'wxdraw': 'draw',
    'wxplot2d': 'plot2d', 'wxplot3d': 'plot3d',
    'wximplicit_plot': 'implicit_plot', 'wxcontour_plot': 'contour_plot',
}
RE_WX = re.compile(r'\b(' + '|'.join(WX_VERS_STD) + r')\s*\(')
RE_DRAW = re.compile(r'\b(draw2d|draw3d|draw)\s*\(')
RE_PLOT = re.compile(r'\b(plot2d|plot3d|implicit_plot|contour_plot)\s*\(')
# Commandes dont on garde l'affichage mais dont on masque le résultat retourné
RE_PRINT = re.compile(r'^\s*(print|printf|disp|display|ldisp|grind|for|while|unless)\b\s*\(?')


def normaliser_wx(cmd):
    """wxdraw2d( -> draw2d(, wxplot2d( -> plot2d(, etc. (hors chaînes)."""
    morceaux = re.split(r'("(?:[^"\\]|\\.)*")', cmd)
    for k in range(0, len(morceaux), 2):
        morceaux[k] = RE_WX.sub(lambda m: WX_VERS_STD[m.group(1)] + '(', morceaux[k])
    return ''.join(morceaux)


def generer_script_maxima(cmds, tex_path, tmpdir):
    esc_path = os.path.abspath(tex_path).replace('\\', '/')
    script = [
        'texput(matrix, ["pmatrix"]);',
        'display2d: false;',
        'load(draw);',
        'load(implicit_plot);',
        '_prev : false;',
        f'with_stdout("{esc_path}",'
    ]

    for i, (cmd_orig, silencieux) in enumerate(cmds, 1):
        cmd_esc = (cmd_orig.replace('\\', '\\\\').replace('"', '\\"')
                   .replace('\n', MARQUE_NL))
        cmd = remplacer_pourcent(normaliser_wx(cmd_orig))
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
            masquer = silencieux or bool(RE_PRINT.match(cmd))
            script.append(f'  val : errcatch({cmd}),')
            if masquer:
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
\usepackage[french]{babel}
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage[useregional]{datetime2}
\usepackage{listings}
\usepackage{xcolor}

% Configuration pour les commandes (avec retour à la ligne automatique)
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

% Configuration pour permettre les retours à la ligne dans les formules mathématiques
\allowdisplaybreaks

\pagestyle{fancy}
\lhead{} \chead{} \rhead{}
\cfoot{ }
\rfoot{page \thepage}
\lfoot{G\'en\'er\'e le \DTMnow}
\renewcommand{\headrulewidth}{0.0pt}
\renewcommand{\footrulewidth}{0.5pt}
\title{Résultats Maxima (Yamwi)}
\author{Généré automatiquement}
\begin{document}
\noindent\fbox{\begin{minipage}{\textwidth}\centering\LARGE\scshape Génération Maxima LaTeX-PDF\end{minipage}}
"""


def decouper_elements(contenu):
    """Découpe une liste TeX aux virgules de premier niveau uniquement.
    Ignore '\\,' (espace fine) et les virgules dans accolades, parenthèses ou crochets internes."""
    parties, courant, profondeur = [], [], 0
    for idx, ch in enumerate(contenu):
        if ch in '[({':
            profondeur += 1
        elif ch in '])}':
            profondeur -= 1
        if ch == ',' and profondeur == 1 and (idx == 0 or contenu[idx - 1] != '\\'):
            courant.append(ch)
            parties.append(''.join(courant))
            courant = []
        else:
            courant.append(ch)
    if courant:
        parties.append(''.join(courant))
    return parties


def ajouter_resultat(body, res_lines):
    """Ajoute à body le bloc LaTeX d'un résultat (lignes accumulées)."""
    # Cas particulier : define / := -> Maxima produit un bloc verbatim (pas une formule)
    m = re.search(r'\\begin\{verbatim\}(.*?)\\end\{verbatim\}',
                  '\n'.join(res_lines), re.DOTALL)
    if m:
        body.append(r"\textcolor{red!70!black}{\textbf{Résultat :}}")
        body.append(r"\begin{lstlisting}[style=commandstyle]")
        # Le ';' final de la sortie tex() n'existe pas dans Maxima : on le retire
        body.extend(ln.strip().rstrip(';') for ln in m.group(1).strip().split('\n'))
        body.append(r"\end{lstlisting}")
        body.append(r"\medskip")
        return

    res_complet = ' '.join(res_lines)
    body.append(r"\textcolor{red!70!black}{\textbf{Résultat :}}")

    if len(res_complet) > 120 and res_complet.startswith('$$') and res_complet.endswith('$$'):
        contenu = res_complet[2:-2].strip()

        if '\\left[' in contenu and '\\right]' in contenu:
            contenu = contenu.replace('\\left', '').replace('\\right', '')

            # Découpage : 10 éléments complets par ligne
            elements = decouper_elements(contenu)
            lignes = [''.join(elements[k:k + 10]).strip()
                      for k in range(0, len(elements), 10)]
            if lignes:
                lignes[-1] = lignes[-1].rstrip(',').strip()

            if len(lignes) > 1:
                body.append(r"\begin{flushleft}")
                body.append("$\\displaystyle \\begin{aligned}")
                for ligne in lignes:
                    body.append(f"&{ligne} \\\\")
                body[-1] = body[-1][:-3]          # enlever le dernier ' \\'
                body.append("\\end{aligned}$")
                body.append(r"\end{flushleft}")
                return

        body.append(r"\begin{flushleft}")
        body.append(f"$\\displaystyle {contenu}$")
        body.append(r"\end{flushleft}")
    else:
        body.append(r"\begin{flushleft}")
        body.append("$\\displaystyle " + res_complet.strip('$') + "$")
        body.append(r"\end{flushleft}")


def finaliser_tex(tmp_tex, font_size, img_width):
    if not os.path.exists(tmp_tex):
        return False
    with open(tmp_tex, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    header = HEADER.replace("FONTSIZE", font_size)
    body = []
    in_res = False
    in_cmd = False
    res_lines = []
    out_lines = []

    def vider_sortie():
        if out_lines:
            body.append(r"\textcolor{green!40!black}{\textbf{Affichage :}}")
            body.append(r"\begin{lstlisting}[style=commandstyle]")
            body.extend(out_lines)
            body.append(r"\end{lstlisting}")
            body.append(r"\medskip")
            out_lines.clear()

    for line in lines:
        l = line.strip()
        if l.startswith("ID:"):
            body.append(f"\\subsection*{{Calcul {l.split(':')[-1].strip()}}}")
        elif l.startswith("CMD:"):
            c = l[len("CMD:"):].strip()
            body.append(r"\textcolor{blue}{\textbf{Commande :}}")
            body.append(r"\begin{lstlisting}[style=commandstyle]")
            body.extend(c.split(MARQUE_NL))
            body.append(r"\end{lstlisting}")
            body.append(r"\medskip")
            in_cmd = True
            in_res = False
            out_lines.clear()
        elif l.startswith("RES:"):
            vider_sortie()
            in_cmd = False
            in_res = True
            res_lines = []
        elif l.startswith("GFX:"):
            vider_sortie()
            in_cmd = False
            img = l[len("GFX:"):].strip()
            body.append(f"\\begin{{center}}\\includegraphics[width={img_width}\\textwidth]{{{img}}}\\end{{center}}")
        elif l.startswith("---BLOCK---"):
            vider_sortie()
            if in_res and res_lines:
                ajouter_resultat(body, res_lines)
            in_res = False
            in_cmd = False
            res_lines = []
        elif in_res and l:
            res_lines.append(l)
        elif in_cmd and l:
            out_lines.append(l)

    vider_sortie()
    if in_res and res_lines:
        ajouter_resultat(body, res_lines)

    with open(tmp_tex, 'w', encoding='utf-8') as f:
        f.write(header + "\n".join(body) + "\n" + r"\end{document}")
    return True


# --- INTERFACE GRAPHIQUE ---

class YamwiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Éditeur Maxima vers LaTeX et PDF - v3.0")
        self.root.geometry("600x750")
        self.pdf_generated_path = None
        self.tmp_dir = None

        tk.Label(root, text="Entrez ou collez vos commandes Maxima :",
                 font=("Arial", 10, "bold")).pack(pady=5)
        self.txt_input = scrolledtext.ScrolledText(root, width=70, height=18, font=("Courier", 11))
        self.txt_input.pack(padx=10, pady=5)

        # Raccourci "Tout sélectionner" (Ctrl+A, et Cmd+A sous macOS)
        for seq in ("<Control-a>", "<Control-A>", "<Command-a>", "<Command-A>"):
            try:
                self.txt_input.bind(seq, self.select_all)
            except tk.TclError:
                pass

        self.txt_input.insert(tk.END, "expand((a+b)^4);\nsolve(x^2 - 5*x + 6 = 0, x);\n"
                                      "draw2d(color=blue, explicit(sin(x), x, 0, 10));")

        opt_frame = tk.LabelFrame(root, text=" Options de rendu ", padx=10, pady=10)
        opt_frame.pack(pady=10, fill=tk.X, padx=10)

        tk.Label(opt_frame, text="Taille police :").grid(row=0, column=0)
        self.font_size = tk.StringVar(value="10pt")
        tk.OptionMenu(opt_frame, self.font_size, "10pt", "11pt", "12pt").grid(row=0, column=1, padx=10)

        tk.Label(opt_frame, text="Largeur images (0.1-1.0) :").grid(row=0, column=2)
        self.img_scale = tk.DoubleVar(value=0.5)
        tk.Scale(opt_frame, from_=0.1, to=1.0, resolution=0.1, orient=tk.HORIZONTAL,
                 variable=self.img_scale).grid(row=0, column=3)

        self.btn_gen = tk.Button(root, text="GÉNÉRER LE PDF", command=self.process,
                                 bg="lightblue", font=("Arial", 10, "bold"))
        self.btn_gen.pack(pady=10, ipady=5, fill=tk.X, padx=50)

        action_frame = tk.Frame(root)
        action_frame.pack(pady=5)
        self.btn_import = tk.Button(action_frame, text="Importer .mac",
                                    command=self.import_mac, bg="#fff2b3")
        self.btn_import.pack(side=tk.LEFT, padx=5)
        self.btn_view = tk.Button(action_frame, text="Visualiser PDF",
                                  command=self.view_pdf, state=tk.DISABLED)
        self.btn_view.pack(side=tk.LEFT, padx=5)
        self.btn_save = tk.Button(action_frame, text="Exporter dossier (TeX + Images + PDF)...",
                                  command=self.save_all, state=tk.DISABLED, bg="#d1ffcf")
        self.btn_save.pack(side=tk.LEFT, padx=5)

        tk.Button(root, text="Quitter", command=root.quit, bg="orange").pack(pady=15)

    def select_all(self, event=None):
        self.txt_input.tag_add("sel", "1.0", "end-1c")
        self.txt_input.mark_set("insert", "end-1c")
        self.txt_input.see("insert")
        return "break"

    def import_mac(self):
        chemin = filedialog.askopenfilename(
            title="Importer un fichier Maxima",
            filetypes=[("Fichiers Maxima", "*.mac *.wxm *.txt"), ("Tous les fichiers", "*.*")])
        if not chemin:
            return
        contenu = None
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                with open(chemin, 'r', encoding=enc) as f:
                    contenu = f.read()
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                messagebox.showerror("Erreur", f"Lecture impossible : {e}")
                return
        if contenu is None:
            messagebox.showerror("Erreur", "Encodage du fichier non reconnu.")
            return
        self.txt_input.delete("1.0", tk.END)
        self.txt_input.insert("1.0", contenu.replace('\r\n', '\n'))

    def process(self):
        raw_text = self.txt_input.get("1.0", tk.END)
        cmds = lire_commandes_depuis_texte(raw_text)

        if not cmds:
            messagebox.showerror("Erreur", "La zone de texte est vide.")
            return

        self.tmp_dir = tempfile.mkdtemp()
        tex_path = os.path.join(self.tmp_dir, "out.tex")
        drv_path = os.path.join(self.tmp_dir, "drv.mac")

        try:
            with open(drv_path, 'w', encoding='utf-8') as f:
                f.write(generer_script_maxima(cmds, tex_path, self.tmp_dir))

            subprocess.run(['maxima', '--very-quiet', '-b', drv_path], capture_output=True)

            if finaliser_tex(tex_path, self.font_size.get(), self.img_scale.get()):
                subprocess.run(['pdflatex', '-interaction=nonstopmode', 'out.tex'],
                               cwd=self.tmp_dir, capture_output=True)
                pdf_path = os.path.join(self.tmp_dir, "out.pdf")
                if os.path.exists(pdf_path):
                    self.pdf_generated_path = pdf_path
                    self.btn_view.config(state=tk.NORMAL)
                    self.btn_save.config(state=tk.NORMAL)
                    messagebox.showinfo("Succès", "Traitement terminé avec succès.")
                else:
                    messagebox.showerror("Erreur", "Erreur lors de la compilation LaTeX.")
            else:
                messagebox.showerror("Erreur", "Maxima n'a pas pu traiter les commandes.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

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
            title="Choisir le nom du dossier d'export",
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

                messagebox.showinfo("Exportation",
                                    f"Dossier créé : {export_dir}\nFichiers : PDF, TeX et {count_img} image(s).")
            except Exception as e:
                messagebox.showerror("Erreur", f"Échec de l'exportation : {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = YamwiApp(root)
    root.mainloop()