# News — version 3.0

*Version française plus bas / French version below.*

---

## English

### Version 3.0 — what's new since 2.0

**Maxima input**
- **Previous result `%`**: `%` now refers to the result of the previous command (e.g. `(x+1)^2;` then `expand(%);`). Constants such as `%pi`, `%e`, `%i` and strings containing `%` are left untouched.
- **Multi-line commands**: a command can span several lines. It ends at the first `;` or `$` found outside a string or a comment. Several commands on the same line are also supported.
- **Comments**: `/* ... */` comments (including nested and multi-line ones) are ignored. Lines starting with `*`, `%%` or `#` are also treated as comments.
- **`$` terminator**: commands ending with `$` are now accepted. The option `SHOW_RESULT_FOR_DOLLAR` (`AFFICHER_RESULTAT_DOLLAR` in the French version) controls whether their result is displayed.
- **Import `.mac` files**: new **Import .mac** button that loads a Maxima file into the editor (UTF-8, cp1252 and Latin-1 encodings are detected).
- **Select all**: `Ctrl+A` (`Cmd+A` on macOS) now works in the editor.

**Graphics**
- wxMaxima commands are converted automatically: `wxdraw2d`, `wxdraw3d`, `wxdraw`, `wxplot2d`, `wxplot3d`, `wximplicit_plot`, `wxcontour_plot`.
- Support for `implicit_plot` and `contour_plot`, and for `draw` with several scenes.

**PDF / LaTeX output**
- **Colored labels**: *Command* in blue, *Result* in dark red, *Output* in green.
- **Output of `print`, `printf`, `disp`, `display`, `for`, `while`…** is now captured and shown in a dedicated *Output* block (previously lost). The returned value is no longer repeated as a *Result*.
- **Maxima messages** (e.g. errors) are displayed in the *Output* block.
- **Function definitions** (`define`, `:=`) are shown as plain text, without the trailing `;`, and with normal spacing.
- **Long lists** are split into lines of 10 complete elements. This fixes a LaTeX compilation error on elements such as `\frac{5\pi}{6}` produced by Maxima.
- Commands containing backslashes or quotes are displayed correctly.

**Platforms and languages**
- Linux and Windows versions, each available in **French** and **English**.
- On Windows, `maxima.bat` is used and paths are passed to Maxima with `/`.

### Requirements
Maxima, gnuplot (for graphics) and a LaTeX distribution providing `pdflatex` must be installed and available in the `PATH`.

### Known limitations
- Animation commands (e.g. `wxanimate_draw`, `with_slider_draw`) are not supported, since the output is a PDF/LaTeX file.
- `%o1`, `%i1`, `%th(n)` are not supported; use `%` for the previous result.

---

## Français

### Version 3.0 — nouveautés depuis la 2.0

**Saisie Maxima**
- **Résultat précédent `%`** : `%` désigne désormais le résultat de la commande précédente (par ex. `(x+1)^2;` puis `expand(%);`). Les constantes `%pi`, `%e`, `%i` et les chaînes contenant `%` ne sont pas modifiées.
- **Commandes sur plusieurs lignes** : une commande peut s'étendre sur plusieurs lignes ; elle se termine au premier `;` ou `$` situé hors d'une chaîne ou d'un commentaire. Plusieurs commandes sur la même ligne sont aussi acceptées.
- **Commentaires** : les commentaires `/* ... */` (y compris imbriqués ou sur plusieurs lignes) sont ignorés. Les lignes commençant par `*`, `%%` ou `#` sont aussi des commentaires.
- **Terminateur `$`** : les commandes terminées par `$` sont acceptées. L'option `AFFICHER_RESULTAT_DOLLAR` indique si leur résultat est affiché.
- **Import de fichiers `.mac`** : nouveau bouton **Importer .mac** qui charge un fichier Maxima dans l'éditeur (encodages UTF-8, cp1252 et Latin-1 détectés).
- **Tout sélectionner** : `Ctrl+A` (`Cmd+A` sous macOS) fonctionne dans l'éditeur.

**Graphiques**
- Les commandes wxMaxima sont converties automatiquement : `wxdraw2d`, `wxdraw3d`, `wxdraw`, `wxplot2d`, `wxplot3d`, `wximplicit_plot`, `wxcontour_plot`.
- Prise en charge de `implicit_plot`, `contour_plot` et de `draw` avec plusieurs scènes.

**Sortie PDF / LaTeX**
- **Libellés en couleur** : *Commande* en bleu, *Résultat* en rouge sombre, *Affichage* en vert.
- **Sortie de `print`, `printf`, `disp`, `display`, `for`, `while`…** : elle est maintenant récupérée et affichée dans un bloc *Affichage* (elle était perdue auparavant). La valeur retournée n'est plus répétée comme *Résultat*.
- **Messages de Maxima** (erreurs, par exemple) : affichés dans le bloc *Affichage*.
- **Définitions de fonctions** (`define`, `:=`) : affichées en texte brut, sans le `;` final, avec un espacement normal.
- **Longues listes** : découpées en lignes de 10 éléments complets. Cela corrige une erreur de compilation LaTeX sur des éléments comme `\frac{5\pi}{6}` produits par Maxima.
- Les commandes contenant des barres obliques inverses ou des guillemets s'affichent correctement.

**Plateformes et langues**
- Versions Linux et Windows, chacune disponible en **français** et en **anglais**.
- Sous Windows, `maxima.bat` est utilisé et les chemins transmis à Maxima utilisent `/`.

### Prérequis
Maxima, gnuplot (pour les graphiques) et une distribution LaTeX fournissant `pdflatex` doivent être installés et accessibles dans le `PATH`.

### Limitations connues
- Les commandes d'animation (par ex. `wxanimate_draw`, `with_slider_draw`) ne sont pas prises en charge, la sortie étant un fichier PDF/LaTeX.
- `%o1`, `%i1`, `%th(n)` ne sont pas pris en charge ; utilisez `%` pour le résultat précédent.
