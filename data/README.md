# Reference data files

Files in this directory are bundled with the `irilab2026` library to ensure
reproducible analyses. Each file is documented below.

## tair.gaf.gz

The *Arabidopsis thaliana* Gene Ontology Annotation file (GAF format) from the
GO Consortium. Maps AGI gene identifiers to GO terms.

- **Source:** https://current.geneontology.org/annotations/tair.gaf.gz
- **Downloaded:** <fill in the date you actually downloaded it>
- **Used by:** `02_core_overlap.ipynb` (R1-Q1, Week 3) for functional enrichment.

The file is bundled because the GO Consortium's distribution server returns
HTTP 403 for programmatic access from some networks, including Colab in
some sessions, which would otherwise block enrichment at runtime.