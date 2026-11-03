# Dataset reference

The leakage-controlled PrimeVul manifest is included as gzip-compressed numbered parts. The raw PrimeVul JSONL partitions are intentionally not redistributed in this public repository.

Reconstruct the manifest with:

```bash
cat thesis_primevul_leakage_controlled_manifest.json.gz.part-* > thesis_primevul_leakage_controlled_manifest.json.gz
gzip -dc thesis_primevul_leakage_controlled_manifest.json.gz > thesis_primevul_leakage_controlled_manifest.json
```

Use the original PrimeVul source dataset for the raw partitions, then compare the reconstructed manifest and the scripts in `scripts/` when reproducing the leakage-control step.
