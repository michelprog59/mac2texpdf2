#!/usr/bin/env python3
import sys, os, subprocess, tempfile, shutil, re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext

# --- LOGIQUE DE TRAITEMENT ---

def lire_commandes_depuis_texte(texte):
    # Découpage du texte et nettoyage identique au script original
    lignes = texte.splitlines()
    return [re.sub(r';+$', '', l.strip()) for l in lignes 
            if l.strip() and not l.startswith(('*', '%'))]

def generer_script_maxima(cmds, tex_path, tmpdir):
    esc_path = os.path.abspath(tex_path).replace('\\', '/')
    script = [
        'texput(matrix, ["pmatrix"]);',
        'display2d: false;',
        'load(draw);',
        f'with_stdout("{esc_path}",'
    ]
    for i, cmd in enumerate(cmds, 1):
        cmd_esc = cmd.replace('"', '\\"')
        img_name = f"plot_{i}.png"
        img_path = os.path.join(tmpdir, img_name).replace('\\', '/')
        img_base = img_path.replace(".png", "")
        script.append(f'  print("---BLOCK---"), print("ID: {i}"), print("CMD: {cmd_esc}"),')
        if any(x in cmd for x in ['draw2d', 'draw3d', 'plot2d', 'plot3d']):
            if 'draw2d' in cmd:
                gfx_cmd = cmd.replace('draw2d(', f'draw2d(terminal=png, file_name="{img_base}", ')
            elif 'draw3d' in cmd:
                gfx_cmd = cmd.replace('draw3d(', f'draw3d(terminal=png, file_name="{img_base}", ')
            elif 'plot2d' in cmd:
                gfx_cmd = re.sub(r'\)$', f', [png_file, "{img_path}"] )', cmd)
            elif 'plot3d' in cmd:
                gfx_cmd = re.sub(r'\)$', f', [png_file, "{img_path}"] )', cmd)
            script.append(f'  errcatch({gfx_cmd}), print("GFX: {img_name}"),')
        else:
            script.append(f'  val : errcatch({cmd}),')
            script.append('  if val = [] then print("RES: MATH_ERR") else (print("RES:"), tex(val[1], true)),')
    script[-1] = script[-1].rstrip(',')
    script.append('); quit();')
    return '\n'.join(script)

def finaliser_tex(tmp_tex, font_size, img_width):
    if not os.path.exists(tmp_tex): return False
    with open(tmp_tex, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # IMPROVED PREAMBLE WITH LINE WRAPPING MANAGEMENT
    header = r"""\documentclass[FONTSIZE]{article}
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

% Configuration for commands (with automatic line wrapping)
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

% Configuration to allow line breaks in mathematical formulas
\allowdisplaybreaks

\pagestyle{fancy}
\lhead{} \chead{} \rhead{}
\cfoot{ }
\rfoot{page \thepage}
\lfoot{Generated on \DTMnow}
\renewcommand{\headrulewidth}{0.0pt}
\renewcommand{\footrulewidth}{0.5pt}
\title{Maxima Results to LaTeX/PDF (Yamwi)}
\author{Generated automatically}
\begin{document}
\noindent\fbox{\begin{minipage}{\textwidth}\centering\LARGE\scshape Maxima LaTeX-PDF Generation\end{minipage}}
"""
    header = header.replace("FONTSIZE", font_size)
    body = []
    in_res = False
    res_lines = []  # Pour accumuler les lignes de résultat
    
    for line in lines:
        l = line.strip()
        if "ID:" in l: 
            body.append(f"\\subsection*{{Calculation {l.split(':')[-1].strip()}}}")
        elif "CMD:" in l:
            c = l.split('CMD:')[-1].strip()
            # Using listings to allow automatic line wrapping
            body.append(r"\textbf{Command :}")
            body.append(r"\begin{lstlisting}[style=commandstyle]")
            body.append(c)
            body.append(r"\end{lstlisting}")
            body.append(r"\medskip")
        elif "RES:" in l: 
            in_res = True
            res_lines = []
            continue
        elif "GFX:" in l:
            img = l.split('GFX:')[-1].strip()
            body.append(f"\\begin{{center}}\\includegraphics[width={img_width}\\textwidth]{{{img}}}\\end{{center}}")
        elif "---BLOCK---" in l:
            # Fin d'un bloc : traiter les résultats accumulés
            if in_res and res_lines:
                res_complet = ' '.join(res_lines)
                
                body.append(r"\textbf{Result :}")
                
                # Pour les très longs résultats, traiter spécialement
                if len(res_complet) > 120 and res_complet.startswith('$$') and res_complet.endswith('$$'):
                    # Extraire le contenu sans les $$
                    contenu = res_complet[2:-2].strip()
                    
                    # Pour les listes simples (comme [1,2,3,...]), découper manuellement
                    if '\\left[' in contenu and '\\right]' in contenu:
                        # Supprimer \left et \right
                        contenu = contenu.replace('\\left', '').replace('\\right', '')
                        
                        # Découper tous les 10 éléments (environ tous les 30-40 caractères)
                        parties = contenu.split(',')
                        lignes = []
                        ligne_temp = ""
                        
                        for i, partie in enumerate(parties):
                            if i == 0:
                                ligne_temp = partie + ','
                            elif (i % 10 == 0):
                                lignes.append(ligne_temp.strip())
                                ligne_temp = partie + ','
                            else:
                                ligne_temp += partie + ','
                        
                        # Ajouter la dernière ligne (enlever la dernière virgule)
                        if ligne_temp:
                            lignes.append(ligne_temp.rstrip(',').strip())
                        
                        # Afficher en utilisant aligned
                        if len(lignes) > 1:
                            body.append(r"\begin{flushleft}")
                            body.append("$\\displaystyle \\begin{aligned}")
                            for ligne in lignes:
                                body.append(f"&{ligne} \\\\")
                            # Enlever le dernier \\
                            body[-1] = body[-1].rstrip(' \\\\')
                            body.append("\\end{aligned}$")
                            body.append(r"\end{flushleft}")
                        else:
                            body.append(r"\begin{flushleft}")
                            body.append(f"$\\displaystyle {contenu}$")
                            body.append(r"\end{flushleft}")
                    else:
                        # Pour les autres types de résultats longs
                        body.append(r"\begin{flushleft}")
                        body.append(f"$\\displaystyle {contenu}$")
                        body.append(r"\end{flushleft}")
                else:
                    # Résultat normal
                    body.append(r"\begin{flushleft}")
                    body.append("$\\displaystyle " + res_complet.strip('$') + "$")
                    body.append(r"\end{flushleft}")
            in_res = False
            res_lines = []
        elif in_res and l:
            # Accumuler les lignes de résultat
            res_lines.append(l)
    
    # Traiter le dernier résultat si la boucle se termine sans ---BLOCK---
    if in_res and res_lines:
        res_complet = ' '.join(res_lines)
        
        body.append(r"\textbf{Result :}")
        
        # Pour les très longs résultats, traiter spécialement
        if len(res_complet) > 120 and res_complet.startswith('$$') and res_complet.endswith('$$'):
            # Extraire le contenu sans les $$
            contenu = res_complet[2:-2].strip()
            
            # Pour les listes simples (comme [1,2,3,...]), découper manuellement
            if '\\left[' in contenu and '\\right]' in contenu:
                # Supprimer \left et \right
                contenu = contenu.replace('\\left', '').replace('\\right', '')
                
                # Découper tous les 10 éléments (environ tous les 30-40 caractères)
                parties = contenu.split(',')
                lignes = []
                ligne_temp = ""
                
                for i, partie in enumerate(parties):
                    if i == 0:
                        ligne_temp = partie + ','
                    elif (i % 10 == 0):
                        lignes.append(ligne_temp.strip())
                        ligne_temp = partie + ','
                    else:
                        ligne_temp += partie + ','
                
                # Ajouter la dernière ligne (enlever la dernière virgule)
                if ligne_temp:
                    lignes.append(ligne_temp.rstrip(',').strip())
                
                # Afficher en utilisant aligned
                if len(lignes) > 1:
                    body.append(r"\begin{flushleft}")
                    body.append("$\\displaystyle \\begin{aligned}")
                    for ligne in lignes:
                        body.append(f"&{ligne} \\\\")
                    # Enlever le dernier \\
                    body[-1] = body[-1].rstrip(' \\\\')
                    body.append("\\end{aligned}$")
                    body.append(r"\end{flushleft}")
                else:
                    body.append(r"\begin{flushleft}")
                    body.append(f"$\\displaystyle {contenu}$")
                    body.append(r"\end{flushleft}")
            else:
                # Pour les autres types de résultats longs
                body.append(r"\begin{flushleft}")
                body.append(f"$\\displaystyle {contenu}$")
                body.append(r"\end{flushleft}")
        else:
            # Résultat normal
            body.append(r"\begin{flushleft}")
            body.append("$\\displaystyle " + res_complet.strip('$') + "$")
            body.append(r"\end{flushleft}")
    
    with open(tmp_tex, 'w', encoding='utf-8') as f:
        f.write(header + "\n".join(body) + r"\end{document}")
    return True

# --- INTERFACE GRAPHIQUE ---

class YamwiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Maxima Editor to LaTeX and PDF - v2.0")
        self.root.geometry("600x750")
        self.pdf_generated_path = None
        self.tmp_dir = None

        # Zone de saisie
        tk.Label(root, text="Enter or paste your Maxima commands :", font=("Arial", 10, "bold")).pack(pady=5)
        self.txt_input = scrolledtext.ScrolledText(root, width=70, height=18, font=("Courier", 11))
        self.txt_input.pack(padx=10, pady=5)
        
        # Exemple par défaut
        self.txt_input.insert(tk.END, "expand((a+b)^4);\nsolve(x^2 - 5*x + 6 = 0, x);\ndraw2d(color=blue, explicit(sin(x), x, 0, 10));")

        # Options de mise en page
        opt_frame = tk.LabelFrame(root, text=" Rendering options ", padx=10, pady=10)
        opt_frame.pack(pady=10, fill=tk.X, padx=10)

        tk.Label(opt_frame, text="Font size :").grid(row=0, column=0)
        self.font_size = tk.StringVar(value="10pt")
        tk.OptionMenu(opt_frame, self.font_size, "10pt", "11pt", "12pt").grid(row=0, column=1, padx=10)

        tk.Label(opt_frame, text="Scale factor (0.1-1.0) :").grid(row=0, column=2)
        self.img_scale = tk.DoubleVar(value=0.5)
        tk.Scale(opt_frame, from_=0.1, to=1.0, resolution=0.1, orient=tk.HORIZONTAL, variable=self.img_scale).grid(row=0, column=3)

        # Bouton Générer
        self.btn_gen = tk.Button(root, text="GENERATE PDF", command=self.process, bg="lightblue", font=("Arial", 10, "bold"))
        self.btn_gen.pack(pady=10, ipady=5, fill=tk.X, padx=50)

        # Actions après génération
        action_frame = tk.Frame(root)
        action_frame.pack(pady=5)
        self.btn_view = tk.Button(action_frame, text="View PDF", command=self.view_pdf, state=tk.DISABLED)
        self.btn_view.pack(side=tk.LEFT, padx=5)
        
        self.btn_save = tk.Button(action_frame, text="Export Folder (TeX + Images + PDF)...", 
                                 command=self.save_all, state=tk.DISABLED, bg="#d1ffcf")
        self.btn_save.pack(side=tk.LEFT, padx=5)

        tk.Button(root, text="Quit", command=root.quit, bg="orange").pack(pady=15)

    def process(self):
        raw_text = self.txt_input.get("1.0", tk.END)
        cmds = lire_commandes_depuis_texte(raw_text)
        
        if not cmds:
            messagebox.showerror("Error", "The text area is empty.")
            return

        self.tmp_dir = tempfile.mkdtemp()
        tex_path = os.path.join(self.tmp_dir, "out.tex")
        drv_path = os.path.join(self.tmp_dir, "drv.mac")

        try:
            with open(drv_path, 'w', encoding='utf-8') as f:
                f.write(generer_script_maxima(cmds, tex_path, self.tmp_dir))
            
            subprocess.run(['maxima', '--very-quiet', '-b', drv_path], capture_output=True)
            
            if finaliser_tex(tex_path, self.font_size.get(), self.img_scale.get()):
                subprocess.run(['pdflatex', '-interaction=nonstopmode', 'out.tex'], cwd=self.tmp_dir, capture_output=True)
                
                pdf_path = os.path.join(self.tmp_dir, "out.pdf")
                if os.path.exists(pdf_path):
                    self.pdf_generated_path = pdf_path
                    self.btn_view.config(state=tk.NORMAL)
                    self.btn_save.config(state=tk.NORMAL)
                    messagebox.showinfo("Success", "Processing completed successfully.")
                else:
                    messagebox.showerror("Error", "Error during LaTeX compilation.")
            else:
                messagebox.showerror("Error", "Maxima could not process the commands.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def view_pdf(self):
        if self.pdf_generated_path:
            if sys.platform == "win32": os.startfile(self.pdf_generated_path)
            elif sys.platform == "darwin": subprocess.run(['open', self.pdf_generated_path])
            else: subprocess.run(['xdg-open', self.pdf_generated_path])

    def save_all(self):
        if not self.pdf_generated_path or not self.tmp_dir: return

        full_dest_path = filedialog.asksaveasfilename(
            title="Choose the name of the export folder",
            initialfile="export_session"
        )
        
        if full_dest_path:
            export_dir = full_dest_path + "_folder"
            try:
                if not os.path.exists(export_dir): os.makedirs(export_dir)
                
                base_name = os.path.basename(full_dest_path)
                shutil.copy2(self.pdf_generated_path, os.path.join(export_dir, base_name + ".pdf"))
                shutil.copy2(os.path.join(self.tmp_dir, "out.tex"), os.path.join(export_dir, base_name + ".tex"))
                
                count_img = 0
                for file in os.listdir(self.tmp_dir):
                    if file.endswith(".png"):
                        shutil.copy2(os.path.join(self.tmp_dir, file), os.path.join(export_dir, file))
                        count_img += 1
                
                messagebox.showinfo("Exportation", f"Folder created : {export_dir}\nFiles : PDF, TeX and {count_img} image(s).")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export : {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = YamwiApp(root)
    root.mainloop()
