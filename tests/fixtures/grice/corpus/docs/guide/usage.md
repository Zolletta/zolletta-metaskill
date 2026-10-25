# Usage Guide

The `render` command reads one template and writes one PDF beside it.

## Rendering

Pass the template path as the only argument, and the command writes the output file next to the template it read.

## Errors

A template with an unknown field fails with a non-zero exit code and prints the offending field name.
