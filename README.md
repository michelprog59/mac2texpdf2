**mac2texpdf2 : a utility for generating a pdf file from maxima commands**

**Version 2.0 dated 2026-02-13**
Author: Michel Gosse, michel.gosse@free.fr


# Overview 

This software is a utility that allows you to enter commands for the
Maxima software (either by typing them or after a copy/paste) which
generates a PDF file containing the entered commands as well as the
results calculated by Maxima. It also allows the export of the LaTeX
file used to produce the PDF as well as the document images to a folder
chosen by the user.

## Screenshots 


<figure>
<p><img src="img1mac2tex.png" style="width:45.0%" alt="image" /> <img
src="img3mac2tex.png" style="width:45.0%" alt="image" /></p>
</figure>

## Software Principle {#software-principle .unnumbered}

The software sends commands to the Maxima computer algebra system (line
by line), which executes them and returns the result in LaTeX. The
software retrieves this data and formats it in a LaTeX document which is
then compiled with pdflatex. It is a Python script, which is also
available as an executable for Windows or Linux.

## Comparison with wxMaxima {#comparison-with-wxmaxima .unnumbered}

This utility is a lightweight and fast tool that allows you to quickly
obtain a high-quality document containing the results calculated by
Maxima from commands entered by the user (in PDF or LaTeX format). It
does not offer the power of wxMaxima and is not suitable for solving
complex exercises.

## Prerequisites {#prerequisites .unnumbered}

To function, the software requires:

1.  Maxima software

2.  Gnuplot software

3.  A LaTeX distribution including the following packages: xcolor,
    listings, datetime2, babel, geometry, fancyhdr, lastpage, graphicx,
    mathtools, amsmath, amsfonts, asmssymb

4.  If you wish to use the source version (the Python script), then
    Python must also be installed on the computer.

*The various installations are detailed by operating system below.*

# Installation for Windows {#installation-for-windows .unnumbered}

## Step 1: Install Maxima and add Maxima to the PATH {#step-1-install-maxima-and-add-maxima-to-the-path .unnumbered}

-> Download and install Maxima (version 5.49.0):

<https://sourceforge.net/projects/maxima/files/Maxima-Windows/5.49.0-Windows/>

-> Modify environment variables:

1.  Open settings: Windows Key + I

2.  Go to System → About.

3.  Click on Advanced system settings.

4.  In the window that opens, click on the Environment Variables...
    button at the bottom

5.  Choose PATH and modify

6.  Add the two lines at the end of the text\
    C:\\maxima-5.49.01 \\bin\
    C:\\maxima-5.49.01 \\gnuplot \\bin

7.  Validate with OK several times to close all windows

*Note*: Gnuplot software is automatically installed at the same time as
Maxima.

## Step 2: Installation of a LaTeX distribution {#step-2-installation-of-a-latex-distribution .unnumbered}

If LaTeX is installed, verify that the packages xcolor, listings,
datetime2, babel, geometry, fancyhdr, lastpage, graphicx, mathtools,
amsmath, amsfonts, asmssymb are properly installed.

Otherwise, download the Texlive distribution and install it (it
automatically installs all required packages and modifies the PATH
directly):

<https://tug.org/texlive/windows.html>

## Step 3 (optional): Python installation {#step-3-optional-python-installation .unnumbered}

If you wish to use the Python script and not the executable, you must
install Python (the installation also adds it to the PATH
automatically).

<https://www.python.org/downloads/windows/>

## Step 4: Download the mac2texpdf2-eng.exe software {#step-4-download-the-mac2texpdf2-eng.exe-software .unnumbered}

Download the Windows version from the page:

<https://maxima-french-doc.fr/interfaces/>

You just need to unzip the file and double-click on the Windows
executable retrieved (it is called mac2texpdf2-eng-w.exe).

Windows issues a warning indicating that the software is not certified.
To launch it, you must accept to run unknown software\...

**Alternative with Python: download the Python script
mac2texpdf2-eng-w.py**

Once unzipped, you need to open a command prompt, navigate to the folder
containing the Python file, and type the command: *python
mac2texpdf2-eng--w.py*

# Installation for Linux {#installation-for-linux .unnumbered}

## Step 1: Install Maxima {#step-1-install-maxima .unnumbered}

If the software is not installed, you can either install it via your
distribution's package manager, or download it from the page:

<https://sourceforge.net/projects/maxima/files/Maxima-Linux/5.49.0-Linux/>

The PATH is added automatically (unlike Windows).

## Step 2: Install LaTeX {#step-2-install-latex .unnumbered}

To be done with your distribution's package manager. A complete
installation should be performed to have all required packages.
Otherwise, they are contained in the texlive-latex-extra package.

## Step 3 (optional): Python installation {#step-3-optional-python-installation-1 .unnumbered}

If you wish to use the Python script and not the binary, install Python
via your distribution's package manager.

## Step 4: Download the mac2texpdf2-eng.bin software {#step-4-download-the-mac2texpdf2-eng.bin-software .unnumbered}

Download the Linux version from the page:

<https://maxima-french-doc.fr/interfaces/>

You just need to unzip the file and double-click on the Linux binary
retrieved (it is called mac2texpdf2-eng.bin).

**Alternative with Python: download the Python script
mac2texpdf2-eng.py**

Once unzipped, you need to open a terminal, navigate to the folder
containing the Python file, and type the command: *python3
mac2texpdf2-eng.py*

# Using mac2texpdf2 {#using-mac2texpdf2 .unnumbered}

The operation is very simple:

-   Enter a series of Maxima commands in the text area. *Each command is
    on a single line and must end with a ;*

-   Choose the font size for the PDF that will be generated. If there
    are graphics, choose the scale for the graphics (between 0 and 1).

-   Click on Generate PDF

-   Click on View PDF.

-   If you want to retrieve the PDF and the corresponding LaTeX file
    (with the document images), click on the export folder button.

## Some points of attention {#some-points-of-attention .unnumbered}

-   For graphics, use the draw2d and draw3d commands. The wxdraw2d and
    wsdraw3d commands are specific to wxMaxima software and are not
    recognized by Maxima which ignores them.

-   Since Maxima input/output is not numbered by mac2texpdf2 software,
    you cannot use % to designate the previous result. For example:

        solve(a*x^2-1=0,x);
        subst(5,a,%);

    does not work. Instead, each result must be named to be used later:

        eq:solve(a*x^2-1=0,x);
        subst(5,a,eq);

# Links and references {#links-and-references .unnumbered}

## Maxima documentation {#maxima-documentation .unnumbered}

<https://maxima-french-doc.fr/documentation/>

## mac2texpdf2 software page {#mac2texpdf2-software-page .unnumbered}

<https://maxima-french-doc.fr/interfaces/>

## mac2texpdf2 software development site {#mac2texpdf2-software-development-site .unnumbered}

The software is under development in a GitHub repository:

<https://github.com/michelprog59/mac2texpdf2>

## License and contact {#license-and-contact .unnumbered}

The software is distributed under the GNU GENERAL PUBLIC LICENSE (GPL)
v3.0 and can be used and modified freely.

For any development requests or bug reports, you can either do so
directly on GitHub, or send me an email at michel.gosse@free.fr
