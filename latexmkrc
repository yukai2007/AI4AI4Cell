# fontspec and the bundled OpenType fonts require a Unicode TeX engine.
# If the project still selects pdfLaTeX, use XeLaTeX for that PDF command.
# Preserve Overleaf/latexmk options (%O) and its source/job naming (%S).
# The native XeLaTeX pipeline remains unchanged when XeLaTeX is selected.
$pdflatex = 'xelatex %O %S';
