# Experiment-output storage format

Most small result files are stored directly in this directory. The larger JSON/JSONL outputs are stored as gzip-compressed parts so that the public GitHub repository remains compatible with GitHub's API upload limits.

## Reconstructing a large output

For a file with parts such as `qwen_test_results.jsonl.gz.part-0001`, concatenate the parts in numeric order and decompress the resulting gzip stream:

```bash
cat qwen_test_results.jsonl.gz.part-* > qwen_test_results.jsonl.gz
gzip -dc qwen_test_results.jsonl.gz > qwen_test_results.jsonl
```

On Windows PowerShell:

```powershell
Get-Content .\qwen_test_results.jsonl.gz.part-* -AsByteStream -ReadCount 0 | Set-Content .\qwen_test_results.jsonl.gz -AsByteStream
gzip -dc .\qwen_test_results.jsonl.gz > .\qwen_test_results.jsonl
```

The part names preserve the original output filename and four-digit order. The original file sizes and SHA-256 checksums are recorded in `../SHA256SUMS.txt` for the uncompressed bundle files.

The compressed-part representation changes only storage format; it does not change the experiment records or their ordering.

