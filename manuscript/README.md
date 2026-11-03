# Manuscript artifacts

The editable manuscript source is stored directly in this directory. The compiled PDF and the literature CSV are gzip-compressed parts because of the repository upload limits.

Reconstruct them by concatenating the numbered parts and decompressing:

```bash
cat main.pdf.gz.part-* > main.pdf.gz
gzip -dc main.pdf.gz > main.pdf

cat scopus_export.csv.gz.part-* > scopus_export.csv.gz
gzip -dc scopus_export.csv.gz > scopus_export.csv
```

The source files `main.tex`, `paper_references.bib`, `references.bib`, the Springer class, bibliography style, and SVG figures are directly readable.
